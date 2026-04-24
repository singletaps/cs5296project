#!/usr/bin/env bash
# EC2: N times same DOCX (default docx_baseline_medium), print one time per line
set -euo pipefail
N="${1:-25}"
ID="${2:-docx_baseline_medium}"
BUCKET="cs5296-project"
URL="http://127.0.0.1:8080/v1/convert/docx-to-pdf"
printf '%s' "{\"input\":{\"bucket\":\"${BUCKET}\",\"key\":\"input/docx/${ID}.docx\"},\"output\":{\"bucket\":\"${BUCKET}\",\"keyPrefix\":\"output/pdf/\"}}" > /tmp/req.json
for i in $(seq 1 "$N"); do
  curl -sS -o /tmp/r.json -w "%{time_total}\n" -X POST "$URL" -H "Content-Type: application/json" --data-binary @/tmp/req.json
  sleep 0.5
done
