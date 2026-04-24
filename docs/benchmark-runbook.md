# Group 259：压测与实验操作手册（含具体命令）

与 [experiment-matrix.md](experiment-matrix.md)、[metrics-definitions.md](metrics-definitions.md) 及 [contracts/openapi.yaml](../contracts/openapi.yaml) 对齐。命令以 **Bash**（Git Bash、WSL、macOS、Linux）为主；在 **Windows PowerShell** 中单独标注。

---

## 0. 环境变量

在每次实验终端中先执行（将占位符换成你们的真实值）：

```bash
export AWS_REGION="ap-east-1"
export AWS_PROFILE="default"
export S3_BUCKET="your-project-bucket"

export BASE_EC2="https://your-alb-xxxx.ap-east-1.elb.amazonaws.com"
export BASE_Lambda="https://xxxx.execute-api.ap-east-1.amazonaws.com/prod/v1"
```

**说明**：`BASE_Lambda` 需与真实 API 路径一致；若已包含 `/v1` 到域名末尾，下文章节中 `curl` 与 k6 使用 `${BASE}/v1/convert/...` 时须避免重复 `v1`（见 7.2）。

**Tier A 与 S3 键**（`id` 同文件名，见 [datasets/manifest.json](../datasets/manifest.json)）：

- 6 个 DOCX：`input/docx/{id}.docx`（id 如 `docx_smoke_001`、`docx_baseline_small` 等）
- 6 个 PDF：`input/pdf/{id}.pdf`

共 12 个对象。

---
## 1. 生成本地 datasets/raw

在仓库**根目录**执行：

```bash
cd /path/to/Project
pip install -r scripts/requirements.txt
python scripts/generate_smoke_assets.py
ls datasets/raw
```

PowerShell：`Get-ChildItem datasets\raw`

**要求**：`manifest.json` 中每条 `sha256` 与 `datasets/raw` 下文件一致；勿用未登记文件混测。

---

## 2. 上传输入到 S3

### 2.1 按前缀同步（推荐）

```bash
aws s3 sync "datasets/raw/" "s3://${S3_BUCKET}/input/docx/" \
  --exclude "*" \
  --include "docx_*.docx" \
  --region "${AWS_REGION}" \
  --profile "${AWS_PROFILE}"

aws s3 sync "datasets/raw/" "s3://${S3_BUCKET}/input/pdf/" \
  --exclude "*" \
  --include "pdf_*.pdf" \
  --region "${AWS_REGION}" \
  --profile "${AWS_PROFILE}"
```

### 2.2 单文件上传

```bash
aws s3 cp "datasets/raw/docx_smoke_001.docx" \
  "s3://${S3_BUCKET}/input/docx/docx_smoke_001.docx" \
  --region "${AWS_REGION}"
```

### 2.3 列桶确认

```bash
aws s3 ls "s3://${S3_BUCKET}/input/docx/" --region "${AWS_REGION}"
aws s3 ls "s3://${S3_BUCKET}/input/pdf/" --region "${AWS_REGION}"
```

---

## 3. 健康检查

仅对**已**映射 `GET /health` 的入口执行：

```bash
curl -sS -o /dev/null -w "http_code=%{http_code} time_total_sec=%{time_total}\n" \
  "${BASE_EC2}/health"
```

若 **API Gateway** 上未挂 `/health`（常 404），可跳过，直接用第 4 节 smoke 转换作存活探针。

PowerShell 示例（EC2 有 `/health` 时）：

```powershell
Invoke-RestMethod -Uri "$env:BASE_EC2/health" -Method Get
```

---
## 4. 单请求功能测试

先执行 `export S3_BUCKET=...`（Bash）或 `[Environment]::SetEnvironmentVariable`（如需要）。

### 4.1 DOCX 到 PDF（smoke）

**Bash**（响应体在 `/tmp/resp_docx.json`，终端打印 `time_total_sec`）：

```bash
curl -sS -o /tmp/resp_docx.json -w "http_code=%{http_code} time_total_sec=%{time_total}\n" \
  -X POST "${BASE_EC2}/v1/convert/docx-to-pdf" \
  -H "Content-Type: application/json" \
  -d "{\"input\":{\"bucket\":\"${S3_BUCKET}\",\"key\":\"input/docx/docx_smoke_001.docx\"},\"output\":{\"bucket\":\"${S3_BUCKET}\",\"keyPrefix\":\"output/pdf/\"}}"
cat /tmp/resp_docx.json
```

**Lambda 端**（`BASE_Lambda` 已含到 `/v1` 为前缀，则下式用 `/v1/convert/...`；若 `BASE` 已以 `/v1` 结尾，则把路径中的 `/v1/convert` 改为 `/convert` 以免重复，见 7.2）：

```bash
curl -sS -o /tmp/resp_docx.json -w "http_code=%{http_code} time_total_sec=%{time_total}\n" \
  -X POST "${BASE_Lambda}/v1/convert/docx-to-pdf" \
  -H "Content-Type: application/json" \
  -d "{\"input\":{\"bucket\":\"${S3_BUCKET}\",\"key\":\"input/docx/docx_smoke_001.docx\"},\"output\":{\"bucket\":\"${S3_BUCKET}\",\"keyPrefix\":\"output/pdf/\"}}"
```

成功时 JSON 含 `"status":"succeeded"`。课设**端到端**延迟以 `time_total`（或 k6 `http_req_duration`）为准。

**PowerShell 示例**：

```powershell
$body = @{
  input  = @{ bucket = $env:S3_BUCKET; key = "input/docx/docx_smoke_001.docx" }
  output = @{ bucket = $env:S3_BUCKET; keyPrefix = "output/pdf/" }
} | ConvertTo-Json -Depth 4
Measure-Command { Invoke-RestMethod -Uri "$env:BASE_EC2/v1/convert/docx-to-pdf" -Method Post -Body $body -ContentType "application/json; charset=utf-8" }
```

### 4.2 PDF 到图（smoke）

`keyPrefix` 须以 `/` 结尾，且**每个 PDF 一个子目录**（见 [sample-requests.http](../contracts/examples/sample-requests.http)）：

```bash
curl -sS -o /tmp/resp_pdf.json -w "http_code=%{http_code} time_total_sec=%{time_total}\n" \
  -X POST "${BASE_EC2}/v1/convert/pdf-to-images" \
  -H "Content-Type: application/json" \
  -d "{\"input\":{\"bucket\":\"${S3_BUCKET}\",\"key\":\"input/pdf/pdf_smoke_001.pdf\"},\"output\":{\"bucket\":\"${S3_BUCKET}\",\"keyPrefix\":\"output/images/pdf_smoke_001/\"},\"render\":{\"dpi\":150,\"format\":\"png\",\"maxPages\":50,\"pageRange\":null}}"
cat /tmp/resp_pdf.json
```

根据响应中 `output.manifestKey` 拉取 manifest（替换 MANIFEST_KEY）：

```bash
export MANIFEST_KEY="output/images/pdf_smoke_001/实际manifest名.json"
aws s3 cp "s3://${S3_BUCKET}/${MANIFEST_KEY}" - --region "${AWS_REGION}"
```

### 4.3 Tier A 全量（每 id 仅 1 次请求，避免重复发两次 curl）

`BASE` 可设为 `BASE_EC2` 或 `BASE_Lambda`。

**6 个 DOCX**：

```bash
mkdir -p results
export BASE="${BASE_EC2}"
for id in docx_smoke_001 docx_baseline_small docx_baseline_medium docx_baseline_large docx_large_001 docx_large_002; do
  echo "=== ${id} ==="
  curl -sS -o "results/${id}.json" -w "http_code=%{http_code} time_total_sec=%{time_total}\n" \
    -X POST "${BASE}/v1/convert/docx-to-pdf" \
    -H "Content-Type: application/json" \
    -d "{\"input\":{\"bucket\":\"${S3_BUCKET}\",\"key\":\"input/docx/${id}.docx\"},\"output\":{\"bucket\":\"${S3_BUCKET}\",\"keyPrefix\":\"output/pdf/\"}}"
done
```

**6 个 PDF**（`keyPrefix` 用 `id` 分子目录，减轻互相覆盖）：

```bash
for id in pdf_smoke_001 pdf_baseline_small pdf_baseline_medium pdf_baseline_multipage pdf_large_001 pdf_stress_001; do
  echo "=== ${id} ==="
  curl -sS -o "results/${id}.json" -w "http_code=%{http_code} time_total_sec=%{time_total}\n" \
    -X POST "${BASE}/v1/convert/pdf-to-images" \
    -H "Content-Type: application/json" \
    -d "{\"input\":{\"bucket\":\"${S3_BUCKET}\",\"key\":\"input/pdf/${id}.pdf\"},\"output\":{\"bucket\":\"${S3_BUCKET}\",\"keyPrefix\":\"output/images/${id}/\"},\"render\":{\"dpi\":150,\"format\":\"png\",\"maxPages\":50,\"pageRange\":null}}"
done
```

对**另一套架构**改 `BASE` 后重跑，得到 EC2 与 Serverless 各一张表。整理列：`id`、`time_total_sec`、`http_code`、JSON 中 `status`。

---
## 5. Lambda 冷启动与第二次请求

1. 让函数**空闲至少 30 分钟**（与 [metrics-definitions.md](metrics-definitions.md) 一致）。
2. 用 4.1 对 `docx_baseline_small` 发**第一次**请求，记录终端中的 `time_total_sec`。
3. **立即**发**完全相同的**第二次请求，再记录 `time_total_sec`。
4. 在 CloudWatch Logs 中该函数的 **REPORT** 行查找 `Init Duration`（仅冷启动有）。

**CLI 示例**（替换日志组与函数名）：

```bash
export LAMBDA_LOG_GROUP="/aws/lambda/your-lambda-name"
aws logs tail "${LAMBDA_LOG_GROUP}" --since 30m --region "${AWS_REGION}" | findstr "REPORT"
# Linux: | grep "REPORT"
```

**EC2**：若做「进程或容器重启后首请求」，报告中须写明**不是**整机关机冷启。

---

## 6. API Gateway 约 29 秒

经 **API Gateway 同步** 的整条链若常超过约 **29s** 会表现为 **504**；这不等同于应用体中的 `CONVERSION_TIMEOUT`。`pdf_large_001`、`pdf_stress_001` 等经 APIGW 时易失败。报告中请区分：仅经 APIGW 的对比；与 **EC2**、**Lambda Function URL** 或**直连**测得的长任务结果（可单独成表，勿与短任务 p99 混为一条线）。

---

## 7. 压测：k6

### 7.1 安装

- Windows：`choco install k6` 或到 [k6 安装](https://k6.io/docs/get-started/installation/) 下载 MSI，或 `winget install GrafanaLabs.k6`；可执行文件常见路径：`C:\Program Files\k6\k6.exe`  
- macOS：`brew install k6`  
- 验证：`k6 version`

**5 分钟 stages 示例（FURL、DOCX→PDF）**：[benchmarks/k6_furl_docx_5m.js](benchmarks/k6_furl_docx_5m.js)；运行示例：

```text
& "C:\Program Files\k6\k6.exe" run benchmarks/k6_furl_docx_5m.js 2>&1 | Tee-Object results/k6_furl_docx_5m_YYYYMMDD_HHmmss.log
```

可用 `-e BASE=... -e BUCKET=... -e DOCX_KEY=docx_baseline_small` 覆盖默认参数。

### 7.2 新建 `benchmarks/k6_docx_baseline.js`

在仓库中创建目录 `benchmarks/`，并新建文件，内容如下：

```javascript
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE;
const BUCKET = __ENV.BUCKET;

export const options = {
  stages: [
    { duration: "1m", target: 5 },
    { duration: "2m", target: 5 },
    { duration: "1m", target: 0 },
  ],
};

const payload = JSON.stringify({
  input: { bucket: BUCKET, key: "input/docx/docx_baseline_medium.docx" },
  output: { bucket: BUCKET, keyPrefix: "output/pdf/" },
});

export default function () {
  const res = http.post(`${BASE}/v1/convert/docx-to-pdf`, payload, {
    headers: { "Content-Type": "application/json" },
  });
  const ok = check(res, {
    "status 200": (r) => r.status === 200,
    "body succeeded": (r) => r.body && r.body.includes('"succeeded"'),
  });
  if (!ok) {
    console.error(`status=${res.status} body=${String(res.body).slice(0, 200)}`);
  }
  sleep(1);
}
```

**BASE 的填法**（全组须统一）：

- 若 k6 环境变量 `BASE` 为 `https://.../prod`（**不含** `/v1`），则 `http.post` 的 URL 使用 `` `${BASE}/v1/convert/docx-to-pdf` ``。
- 若 `BASE` 已含 `/v1`（例如 `https://.../prod/v1`），则 URL 使用 `` `${BASE}/convert/docx-to-pdf` ``，**不要**再拼一段 `/v1`。

### 7.3 执行并保存日志

在仓库根目录：

```bash
mkdir -p results
k6 run -e BASE="${BASE_EC2}" -e BUCKET="${S3_BUCKET}" \
  benchmarks/k6_docx_baseline.js \
  2>&1 | tee "results/k6_ec2_docx_$(date +%Y%m%d_%H%M%S).log"
```

对 Lambda 改 `BASE`：

```bash
k6 run -e BASE="${BASE_Lambda}" -e BUCKET="${S3_BUCKET}" \
  benchmarks/k6_docx_baseline.js \
  2>&1 | tee "results/k6_lambda_docx_$(date +%Y%m%d_%H%M%S).log"
```

**Windows PowerShell 无 `date` 时**：可用 `k6_$(Get-Date -Format yyyyMMdd_HHmmss).log`。

在日志中记录 **http_req_duration** 的 p50/p90/p99、**iterations**、**失败数**。

### 7.4 PDF 到图压测

复制为 `k6_pdf_baseline.js`，将 `POST` URL 与 `payload` 改为与 4.2 一致，例如 `key` 为 `input/pdf/pdf_baseline_medium.pdf`，`keyPrefix` 为 `output/images/pdf_baseline_medium/`。高并发时同一路径会覆盖；若只测 RPS 可接受，否则降低并发或为每次请求用不同 `keyPrefix`（需自行扩展脚本）。

---
## 8. 需收集数据（课设、报告、Artifact）

| 类别 | 内容 | 来源 |
|------|------|------|
| 可复现 | Region、S3 桶、EC2 与 API 的基 URL、**两镜像** digest、Lambda 内存/超时/临时盘、EC2 类型 | 部署配置、`docker inspect`、控制台截图 |
| 延迟 | p50 / p90 / p99、样本量、成功定义（HTTP 200 且 JSON `status` 为 `succeeded`） | k6 摘要、或 4.3 节中手工汇总 `time_total` |
| 冷启动 | 空闲 30 分钟后首请求、Init Duration 与总延迟 | 4.1 的 curl 与 5. 节 CloudWatch `REPORT` |
| 错误 | 4xx/5xx、504 条数、响应体 `error.code` | k6 失败日志、响应体、（可选）ALB 5xx 计数 |
| 边界与口径 | 是否经 API Gateway、与 EC2/Function URL/直连 的分别 | 实验记录文字说明 |
| Artifact | 本 md、manifest 固定 commit、**k6 脚本路径**、**原始 .log**、S3 前缀说明 | 与公开 GitHub 一致 |

**最低可交**：EC2 与 Serverless 各 1 份 k6 日志、各 1 份 4.3 的逐 id 时延、Lambda 冷启动 1 组与第二次请求的对照、镜像 digest 行。

---

## 9. 相关文档

- [phase0-phase1-implementation.md](phase0-phase1-implementation.md) S3 命名
- [ec2-build-push-ecr-checklist.md](ec2-build-push-ecr-checklist.md)、[converter-ec2-commands.md](converter-ec2-commands.md) EC2/ECR
- [lambda-container-deploy.md](lambda-container-deploy.md) Lambda 容器
- [phase0-phase1-handoff-for-teammate.md](phase0-phase1-handoff-for-teammate.md) 队友对齐表

---

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-04-23 | 初版；命令经 Bash/PowerShell 与 OpenAPI 对齐；中文用 UTF-8 落盘。 |

