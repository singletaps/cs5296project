#!/bin/bash
# Lambda + AWS Lambda Web Adapter: no Gotenberg (DOCX uses soffice CLI in main.py only).
set -euo pipefail
cd /app
exec /opt/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8080
