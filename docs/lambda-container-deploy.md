# Lambda container image (LWA)

Use with [ec2-build-push-ecr-checklist.md](./ec2-build-push-ecr-checklist.md): same repo, **EC2** uses the default build; **Lambda** uses **`--target lambda`** and push to ECR.

## EC2 vs Lambda image

| Item | EC2 (default `docker build`) | Lambda (`--target lambda`) |
|------|------------------------------|----------------------------|
| Final stage | `ec2` | `lambda` |
| Gotenberg :3000 | Yes (entrypoint waits for /health) | **No** (DOCX uses in-app `soffice`; no Gotenberg HTTP) |
| AWS Lambda Web Adapter | No | **Yes** (`/opt/extensions/lambda-adapter`) |
| Process | [entrypoint.sh](../services/converter/entrypoint.sh) | [entrypoint-lambda.sh](../services/converter/entrypoint-lambda.sh) (uvicorn :8080 only) |

Application code is the same: [services/converter/src/main.py](../services/converter/src/main.py).

## Build and push to ECR

```bash
cd services/converter
docker build --target lambda -t "${ECR_URL}/${REPO_NAME}:lambda" .
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_URL}"
docker push "${ECR_URL}/${REPO_NAME}:lambda"
```

Create a **Lambda (container image)** function with that URI. For **Handler**, follow AWS + LWA docs (often leave default).

## Environment

- `AWS_REGION`: match S3 buckets.
- `AWS_LWA_PORT`: default `8080` (set in image `ENV`).
- `AWS_LWA_READINESS_CHECK_PATH`: default `/health` (matches FastAPI `GET /health`).
- `CONVERSION_TIMEOUT_SEC`: align with Lambda **function timeout**; set function timeout slightly above worst-case conversion.

## Ops / limits (reports)

- **Memory**: LibreOffice / large PDF often needs **2048 MB+** (tune in lab).
- **/tmp**: `soffice` uses temp dirs; increase **ephemeral storage** if needed.
- **API Gateway sync**: ~**29s** limit; long jobs may need Function URL, async, or a different comparison (see [experiment-matrix.md](./experiment-matrix.md)).

## Reference

- [AWS Lambda Web Adapter - Docker images](https://aws.github.io/aws-lambda-web-adapter/getting-started/docker-images.html)
