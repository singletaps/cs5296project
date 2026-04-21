# Converter service（Group 259）

同一 Docker 镜像：**Gotenberg 8**（LibreOffice，:3000）+ **poppler**（`pdftoppm`）+ **FastAPI**（:8080）S3 读写封装。

## 构建与运行

```bash
cd services/converter
docker build -t group259-converter:local .
docker run --rm --name g259 -p 8080:8080 -p 3000:3000 \
  -e AWS_REGION=ap-east-1 \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  group259-converter:local
```

- **Windows 检出**：若 `entrypoint.sh` 为 CRLF，镜像内在构建阶段会用 `sed` 去掉 `\r`，避免 `exec /entrypoint.sh: no such file or directory`。仓库已设 [.gitattributes](../../.gitattributes) 尽量统一 LF。
- **快速探活**（容器启动约 5–15s）：`curl http://127.0.0.1:8080/health`；可选 `curl http://127.0.0.1:3000/health` 查看 Gotenberg/LibreOffice 状态。

本地调试可使用 `~/.aws/credentials` 挂载（勿提交密钥）。

## 环境变量

| 变量 | 说明 |
|------|------|
| `AWS_REGION` | 必填（除非实例元数据可用） |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | 本地或 CI；EC2/Lambda 用 IAM 角色时可省略 |
| `GOTENBERG_URL` | 默认 `http://127.0.0.1:3000` |
| `CONVERSION_TIMEOUT_SEC` | Gotenberg HTTP 超时秒数，默认 `300` |

## API

见 [contracts/openapi.yaml](../../contracts/openapi.yaml)。

- `GET /health` — 仅检查 API 进程；生产可扩展为连调 Gotenberg。
- `POST /v1/convert/docx-to-pdf`
- `POST /v1/convert/pdf-to-images`

## 已知限制

- LibreOffice 与 Word 版式非 100% 一致；极个别 DOCX 可能超时或失败（见 Gotenberg 文档）。
- 经 **API Gateway** 同步路由时约 **29s** 上限；长任务需阶段 2 异步或直连测量。
- 镜像较大，Lambda **冷启动**会较慢（符合 benchmark 目标）。

## 版本钉扎

构建后建议记录 digest：

```bash
docker inspect --format='{{index .RepoDigests 0}}' group259-converter:local
```

基础镜像 tag：`gotenberg/gotenberg:8`（随上游浮动；生产可改为 `@sha256:...`）。
