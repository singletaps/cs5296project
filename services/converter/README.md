# Converter service (Group 259)

One Docker build from **Gotenberg 8** (LibreOffice preinstalled) plus **poppler** (`pdftoppm`) and a **FastAPI** wrapper (S3 in/out). **DOCX to PDF** uses the **`soffice` CLI** in-process (not the Gotenberg HTTP API).

## Build and run

**EC2 / local (default `docker build` = target `ec2`: starts Gotenberg on :3000 and the API on :8080)**:

```bash
cd services/converter
docker build -t group259-converter:local .
docker run --rm --name g259 -p 8080:8080 -p 3000:3000 \
  -e AWS_REGION=ap-east-1 \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  group259-converter:local
```

**Lambda (container)**: uses [AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) — only **uvicorn**; **no** Gotenberg process. Same `src/` as EC2. Build with the `lambda` target:

```bash
docker build --target lambda -t group259-converter:lambda .
```

See [docs/lambda-container-deploy.md](../../docs/lambda-container-deploy.md).

- **Windows checkouts**: `Dockerfile` runs `sed` on shell entrypoints to strip `\r` so `/bin/bash` works. The repo has [.gitattributes](../../.gitattributes) for LF where possible.
- **Health checks**: `curl http://127.0.0.1:8080/health` (API). Optional: `curl http://127.0.0.1:3000/health` (Gotenberg) when using the `ec2` image.

For local testing you can mount `~/.aws/credentials` (do not commit secrets).

## Environment variables

| Name | Description |
|------|-------------|
| `AWS_REGION` | Required unless using instance metadata / role |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Local/CI; omit on EC2/Lambda with IAM roles |
| `SOFFICE_PATH` | Optional path to the `soffice` binary; otherwise use `PATH` |
| `CONVERSION_TIMEOUT_SEC` | Subprocess timeout for `soffice` / `pdftoppm` (default `300`) |

## API

See [contracts/openapi.yaml](../../contracts/openapi.yaml).

- `GET /health` — process up (extend for deeper checks in production)
- `POST /v1/convert/docx-to-pdf`
- `POST /v1/convert/pdf-to-images`

## Known limitations

- LibreOffice is not a pixel-perfect Word replacement; a few DOCX may fail or time out.
- **API Gateway** synchronous integration has a ~**29s** cap; use async/Function URL/longer paths for long jobs as appropriate.
- Image size is **large**; expect slower **Lambda cold starts** (useful for benchmarks).

## Pinning the image

After build, record the digest:

```bash
docker inspect --format='{{index .RepoDigests 0}}' group259-converter:local
```

Base: `gotenberg/gotenberg:8` (floating tag; for production you may pin `@sha256:...`).
