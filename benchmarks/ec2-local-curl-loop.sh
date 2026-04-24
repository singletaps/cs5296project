#!/usr/bin/env bash
# Run on EC2: bash ec2-local-curl-loop.sh
set -euo pipefail
BODY="${1:-/tmp/body-docx-pdf.json}"
URL="${2:-http://127.0.0.1:8080/v1/convert/docx-to-pdf}"
for i in 1 2 3 4 5; do
  echo -n "seq_${i} "
  curl -sS -o /tmp/r.json -w "time_total_sec=%{time_total} http=%{http_code}\n" \
    -X POST "$URL" \
    -H "Content-Type: application/json" \
    --data-binary @"$BODY"
  head -c 120 /tmp/r.json
  echo
done
