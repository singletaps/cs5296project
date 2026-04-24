#!/usr/bin/env bash
# On EC2: bash ec2-docx-matrix.sh
set -euo pipefail
BUCKET="cs5296-project"
URL="http://3.88.254.51:8080/v1/convert/docx-to-pdf"
IDS=(docx_smoke_001 docx_baseline_small docx_baseline_medium docx_baseline_large docx_large_001 docx_large_002)
for id in "${IDS[@]}"; do
  printf '%s' "{\"input\":{\"bucket\":\"${BUCKET}\",\"key\":\"input/docx/${id}.docx\"},\"output\":{\"bucket\":\"${BUCKET}\",\"keyPrefix\":\"output/pdf/\"}}" > /tmp/req.json
  echo -n "ID=${id} "
  curl -sS -o /tmp/r.json -w "time_total_sec=%{time_total} http=%{http_code}\n" \
    -X POST "$URL" -H "Content-Type: application/json" --data-binary @/tmp/req.json
  head -c 200 /tmp/r.json
  echo
done
