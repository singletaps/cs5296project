#!/usr/bin/env bash
set -euo pipefail
BUCKET="cs5296-project"
URL="http://127.0.0.1:8080/v1/convert/pdf-to-images"
IDS=(pdf_smoke_001 pdf_baseline_small pdf_baseline_medium pdf_baseline_multipage pdf_large_001 pdf_stress_001)
for id in "${IDS[@]}"; do
  printf '%s' "{\"input\":{\"bucket\":\"${BUCKET}\",\"key\":\"input/pdf/${id}.pdf\"},\"output\":{\"bucket\":\"${BUCKET}\",\"keyPrefix\":\"output/images/${id}/\"},\"render\":{\"dpi\":150,\"format\":\"png\",\"maxPages\":50,\"pageRange\":null}}" > /tmp/req.json
  echo -n "ID=${id} "
  curl -sS -o /tmp/r.json -w "time_total_sec=%{time_total} http=%{http_code}\n" \
    -X POST "$URL" -H "Content-Type: application/json" --data-binary @/tmp/req.json
  head -c 200 /tmp/r.json
  echo
done
