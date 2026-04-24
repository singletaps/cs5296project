/**
 * k6: Lambda Function URL — POST /v1/convert/docx-to-pdf
 * Fixed body: docx_baseline_small (S3 key must exist in cs5296-project).
 * Total stages ~5 minutes; tune BASE/BUCKET/KEY with -e or edit defaults below.
 */
import http from "k6/http";
import { check, sleep } from "k6";

// Override: k6 run -e BASE=https://... -e BUCKET=cs5296-project -e DOCX_KEY=docx_baseline_small
const BASE = __ENV.BASE || "https://w7tivllplqmgmmse6uqknsnn4m0dkosp.lambda-url.us-east-1.on.aws";
const BUCKET = __ENV.BUCKET || "cs5296-project";
const DOCX_STEM = __ENV.DOCX_KEY || "docx_baseline_small";

const PAYLOAD = JSON.stringify({
  input: {
    bucket: BUCKET,
    key: `input/docx/${DOCX_STEM}.docx`,
  },
  output: {
    bucket: BUCKET,
    keyPrefix: "output/pdf/",
  },
});

// 5 minutes total: 30s warm-up 1 VU, ramp to 2, hold, ramp down
export const options = {
  stages: [
    { duration: "30s", target: 1 },
    { duration: "1m", target: 2 },
    { duration: "2m", target: 2 },
    { duration: "1m", target: 2 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.1"],
    http_req_duration: ["p(99)<180000"],
  },
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

const URL = `${BASE}/v1/convert/docx-to-pdf`;

export default function () {
  const res = http.post(URL, PAYLOAD, {
    headers: { "Content-Type": "application/json" },
    timeout: "300s",
  });
  const ok = check(res, {
    "status 200": (r) => r.status === 200,
    "json succeeded": (r) =>
      r.body && (r.body.includes('"status"') && r.body.includes("succeeded")),
  });
  if (!ok) {
    console.error(`status=${res.status} len=${res.body ? res.body.length : 0}`);
  }
  sleep(0.2);
}
