#!/bin/sh
curl -sf "http://127.0.0.1:8080/health" >/dev/null || exit 1
