from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Group259 Converter", version="1.0.0")

CONVERSION_TIMEOUT_SEC = float(os.environ.get("CONVERSION_TIMEOUT_SEC", "300"))


class S3Loc(BaseModel):
    bucket: str
    key: str


class OutputPrefix(BaseModel):
    bucket: str
    keyPrefix: str


class RenderOptions(BaseModel):
    dpi: int = 150
    format: str = "png"
    maxPages: int = Field(default=50, ge=1, le=200)
    pageRange: str | None = None


class DocxToPdfRequest(BaseModel):
    input: S3Loc
    output: OutputPrefix
    clientRequestId: str | None = None


class PdfToImagesOutput(BaseModel):
    bucket: str
    keyPrefix: str


class PdfToImagesRequest(BaseModel):
    input: S3Loc
    output: PdfToImagesOutput
    render: RenderOptions | None = None
    clientRequestId: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


def _fail_response(
    *,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"status": "failed", "error": {"code": error_code, "message": message}}
    if details:
        body["error"]["details"] = details
    if extra:
        body.update(extra)
    return body


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_fail_response(
            error_code="INVALID_INPUT",
            message="Request validation failed",
            details={"errors": exc.errors()},
        ),
    )


def _s3_client():
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION"))


def _normalize_prefix(prefix: str) -> str:
    p = prefix.strip()
    if not p.endswith("/"):
        p += "/"
    return p


def _object_id_from_key(key: str) -> str:
    name = Path(key).name
    stem = Path(name).stem
    if not stem:
        raise ValueError("Cannot derive id from empty key")
    return stem


def _soffice_bin() -> str | None:
    p = os.environ.get("SOFFICE_PATH", "").strip()
    if p and os.path.isfile(p):
        return p
    return shutil.which("soffice")


def _soffice_subprocess_env(work_dir: Path) -> dict[str, str]:
    """LibreOffice needs a writable profile dir; Lambda often has a non-writable or missing $HOME for LO."""
    lo_home = work_dir / "lo_profile"
    config = lo_home / ".config"
    cache = lo_home / ".cache"
    for p in (lo_home, config, cache):
        p.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "HOME": str(lo_home),
        "XDG_CONFIG_HOME": str(config),
        "XDG_CACHE_HOME": str(cache),
    }


def _parse_page_range(page_range: str | None, max_pages: int) -> tuple[int, int]:
    if not page_range:
        return 1, max_pages
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", page_range.strip())
    if not m:
        raise ValueError(f"Invalid pageRange: {page_range!r}")
    first, last = int(m.group(1)), int(m.group(2))
    if first < 1 or last < first:
        raise ValueError("pageRange must have first >= 1 and last >= first")
    last = min(last, first + max_pages - 1)
    return first, last


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/convert/docx-to-pdf")
def convert_docx_to_pdf(req: DocxToPdfRequest):
    started = time.perf_counter()
    try:
        object_id = _object_id_from_key(req.input.key)
    except ValueError as e:
        return JSONResponse(status_code=400, content=_fail_response(error_code="INVALID_INPUT", message=str(e)))

    prefix = _normalize_prefix(req.output.keyPrefix)
    out_key = f"{prefix}{object_id}.pdf"

    s3 = _s3_client()
    try:
        obj = s3.get_object(Bucket=req.input.bucket, Key=req.input.key)
        docx_bytes = obj["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "NotFound"):
            return _fail_response(error_code="OBJECT_NOT_FOUND", message=str(e), details={"bucket": req.input.bucket, "key": req.input.key})
        return _fail_response(error_code="CONVERSION_FAILED", message=f"S3 read failed: {e}")
    except BotoCoreError as e:
        return _fail_response(error_code="CONVERSION_FAILED", message=f"AWS S3 read failed: {e}")

    if not docx_bytes:
        return _fail_response(error_code="INVALID_INPUT", message="Empty DOCX object")

    soffice = _soffice_bin()
    if not soffice:
        return _fail_response(
            error_code="CONVERSION_FAILED",
            message="soffice not found; install LibreOffice or set SOFFICE_PATH",
        )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        in_path = td_path / "input.docx"
        out_path = td_path / "input.pdf"
        in_path.write_bytes(docx_bytes)
        cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(td_path), str(in_path)]
        try:
            cp = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=CONVERSION_TIMEOUT_SEC,
                env=_soffice_subprocess_env(td_path),
            )
        except subprocess.TimeoutExpired:
            return _fail_response(error_code="CONVERSION_TIMEOUT", message="LibreOffice (soffice) conversion timed out")
        if cp.returncode != 0:
            return _fail_response(
                error_code="CONVERSION_FAILED",
                message="LibreOffice (soffice) conversion failed",
                details={
                    "returncode": cp.returncode,
                    "stderr": (cp.stderr or "")[:2000],
                    "stdout": (cp.stdout or "")[:500],
                },
            )
        if not out_path.is_file():
            return _fail_response(
                error_code="CONVERSION_FAILED",
                message="LibreOffice did not produce input.pdf",
                details={"stderr": (cp.stderr or "")[:2000]},
            )
        pdf_bytes = out_path.read_bytes()

    if not pdf_bytes.startswith(b"%PDF"):
        return _fail_response(
            error_code="CONVERSION_FAILED",
            message="Conversion output is not a valid PDF",
        )

    try:
        s3.put_object(
            Bucket=req.output.bucket,
            Key=out_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
    except ClientError as e:
        return _fail_response(error_code="CONVERSION_FAILED", message=f"S3 write failed: {e}")
    except BotoCoreError as e:
        return _fail_response(error_code="CONVERSION_FAILED", message=f"AWS S3 write failed: {e}")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": "succeeded",
        "output": {"bucket": req.output.bucket, "key": out_key},
        "metrics": {"processingMs": elapsed_ms},
    }


@app.post("/v1/convert/pdf-to-images")
def convert_pdf_to_images(req: PdfToImagesRequest):
    started = time.perf_counter()
    render = req.render or RenderOptions()

    if render.format != "png":
        return JSONResponse(
            status_code=400,
            content=_fail_response(error_code="INVALID_INPUT", message='Only render.format "png" is supported in v1'),
        )

    try:
        object_id = _object_id_from_key(req.input.key)
        first_page, last_page = _parse_page_range(render.pageRange, render.maxPages)
    except ValueError as e:
        return JSONResponse(status_code=400, content=_fail_response(error_code="INVALID_INPUT", message=str(e)))

    key_prefix = _normalize_prefix(req.output.keyPrefix)
    s3 = _s3_client()

    try:
        obj = s3.get_object(Bucket=req.input.bucket, Key=req.input.key)
        pdf_bytes = obj["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "NotFound"):
            return _fail_response(error_code="OBJECT_NOT_FOUND", message=str(e), details={"bucket": req.input.bucket, "key": req.input.key})
        return _fail_response(error_code="CONVERSION_FAILED", message=f"S3 read failed: {e}")
    except BotoCoreError as e:
        return _fail_response(error_code="CONVERSION_FAILED", message=f"AWS S3 read failed: {e}")

    if not pdf_bytes:
        return _fail_response(error_code="INVALID_INPUT", message="Empty PDF object")

    tmp_root = Path(tempfile.mkdtemp(prefix="pdfimg_"))
    try:
        pdf_path = tmp_root / "input.pdf"
        pdf_path.write_bytes(pdf_bytes)
        out_base = tmp_root / "page"
        cmd = [
            "pdftoppm",
            "-png",
            "-r",
            str(render.dpi),
            "-f",
            str(first_page),
            "-l",
            str(last_page),
            str(pdf_path),
            str(out_base),
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=int(CONVERSION_TIMEOUT_SEC),
            )
        except subprocess.TimeoutExpired:
            return _fail_response(error_code="CONVERSION_TIMEOUT", message="pdftoppm timed out")
        except subprocess.CalledProcessError as e:
            return _fail_response(
                error_code="CONVERSION_FAILED",
                message="pdftoppm failed",
                details={"stderr": (e.stderr or "")[:2000], "returncode": e.returncode},
            )

        def _page_sort_key(p: Path) -> int:
            m = re.search(r"-(\d+)\.png$", p.name)
            return int(m.group(1)) if m else 0

        produced = sorted(tmp_root.glob(f"{out_base.name}-*.png"), key=_page_sort_key)
        if not produced:
            produced = sorted(
                [p for p in tmp_root.glob("*.png") if p.name.startswith(f"{out_base.name}-")],
                key=_page_sort_key,
            )

        if not produced:
            return _fail_response(error_code="CONVERSION_FAILED", message="No PNG pages produced by pdftoppm")

        try:
            manifest_pages: list[dict[str, Any]] = []
            for idx, src in enumerate(produced, start=1):
                dest_key = f"{key_prefix}page-{idx:04d}.png"
                page_body = src.read_bytes()
                s3.put_object(
                    Bucket=req.output.bucket,
                    Key=dest_key,
                    Body=page_body,
                    ContentType="image/png",
                )
                manifest_pages.append({"page": idx, "key": dest_key})

            manifest_obj = {
                "dpi": render.dpi,
                "format": render.format,
                "sourcePdfKey": req.input.key,
                "pages": manifest_pages,
            }
            manifest_key = f"{key_prefix}manifest.json"
            s3.put_object(
                Bucket=req.output.bucket,
                Key=manifest_key,
                Body=json.dumps(manifest_obj, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
        except ClientError as e:
            return _fail_response(error_code="CONVERSION_FAILED", message=f"S3 write failed: {e}")
        except BotoCoreError as e:
            return _fail_response(error_code="CONVERSION_FAILED", message=f"AWS S3 write failed: {e}")

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "status": "succeeded",
            "output": {
                "bucket": req.output.bucket,
                "manifestKey": manifest_key,
                "pageCount": len(manifest_pages),
            },
            "metrics": {"processingMs": elapsed_ms},
        }
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
