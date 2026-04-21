# CS5296 Group 259 — Document conversion benchmark (EC2 vs Serverless)

Course project: one Docker image runs **DOCX to PDF** (Gotenberg/LibreOffice) and **PDF to PNG** (poppler), deployed on **EC2** vs **Lambda + API Gateway** for performance comparison.

## What your teammate needs (minimal)

1. **Repo layout**: API spec `contracts/openapi.yaml`, dataset list `datasets/manifest.json`, service `services/converter/` (Dockerfile + FastAPI), docs under `docs/`.
2. **Image contents and phase-2 usage**: read and share [`docs/group259-docker-image-handoff.txt`](docs/group259-docker-image-handoff.txt).
3. **Alignment checklist**: [`docs/phase0-phase1-handoff-for-teammate.md`](docs/phase0-phase1-handoff-for-teammate.md) (two AWS accounts, fill-in table).
4. **Build image locally**:
   ```bash
   cd services/converter
   docker build -t group259-converter:local .
   docker run --rm -p 8080:8080 -p 3000:3000 -e AWS_REGION=<region> group259-converter:local
   ```
5. **S3**: valid AWS credentials (or instance/Lambda role); upload test objects per `manifest` and OpenAPI; never commit secrets.
6. **Synthetic test files** (`datasets/raw/` is gitignored): `pip install -r scripts/requirements.txt` then `python scripts/generate_smoke_assets.py`.

## Directory map

| Path | Purpose |
|------|---------|
| `contracts/` | OpenAPI, sample HTTP |
| `datasets/` | `manifest.json`, `README.md` |
| `docs/` | experiment matrix, metrics, phase 0/1 notes, image handoff txt, push instructions |
| `scripts/` | generate synthetic DOCX/PDF |
| `services/converter/` | production image definition and source |

## Push to GitHub (repo name: cs5296project)

Git is initialized with branch `main` and commits are ready. Create an **empty** public repo named **`cs5296project`** on GitHub, then follow [`docs/push-instructions.txt`](docs/push-instructions.txt) to add `origin` and run `git push -u origin main`.

## Course deliverables

Follow CS5296 Canvas: public GitHub for artifact review; report and demo submitted separately.
