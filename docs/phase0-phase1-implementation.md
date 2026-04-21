# 阶段 0 & 阶段 1 详细实施方案（单人独立完成）

**与队友对齐（双 AWS 账号、阶段 2 检查表）**：见 [phase0-phase1-handoff-for-teammate.md](phase0-phase1-handoff-for-teammate.md)。

本文档面向 **Group 259**：在 AWS 上对比 **EC2** 与 **Serverless（Lambda + API Gateway）** 承载同一套 **DOCX→PDF**、**PDF→光栅图像** 工作负载。阶段 0 冻结范围与契约；阶段 1 交付 **单一事实来源** 的转换镜像与本地可跑通验证。

**数据约定**：采用推荐的 `datasets/manifest.json`（或 JSON Lines），含 `id`、`role`、`format`、`source`、`license`、`sha256`、`bytes`、`pages`、`notes`；**Tier A** 为必做固定集，**Tier B** 为可选扩展。

---

## 一、阶段 0：范围冻结与成功标准

### 0.1 交付物清单（你完成阶段 0 时应具备）

| 交付物 | 路径建议 | 说明 |
|--------|----------|------|
| 接口契约 | `contracts/openapi.yaml` | OpenAPI 3.0+，含请求/响应 schema 与错误模型 |
| 数据集清单 | `datasets/manifest.json` | Tier A 全量条目 + 哈希占位（阶段 1 末尾填实 `sha256`） |
| 数据集说明 | `datasets/README.md` | 来源、许可、下载/生成步骤、伦理与脱敏说明 |
| 实验矩阵 | `docs/experiment-matrix.md` | 负载形态 × 输入规模 × 观测指标（表格） |
| 指标与口径 | `docs/metrics-definitions.md` | 延迟起止点、冷启动定义、分位数约定 |
| （可选）示例请求 | `contracts/examples/*.http` 或 `curl` 片段 | 便于队友与压测脚本对齐 |

### 0.2 API 设计（推荐：S3 引用 + 统一错误体）

**原则**：转换在服务端读 S3、写 S3，HTTP body 只传 **元数据**，避免 API Gateway **10MB** 同步 payload 限制与大文件超时混淆。

**建议端点**（可按实现微调，但需在 `openapi.yaml` 中冻结）：

1. `POST /v1/convert/docx-to-pdf`  
2. `POST /v1/convert/pdf-to-images`  
3. （大文件推荐）`POST /v1/jobs` + `GET /v1/jobs/{jobId}` — 若阶段 2 先只做同步，可在 OpenAPI 中标记为 `deprecated` 或 `future`，但阶段 0 应写明 **何时必须异步**（见 0.5）。

**统一请求体（示例字段）**：

```json
{
  "input": {
    "bucket": "your-bucket",
    "key": "input/docx/small_001.docx"
  },
  "output": {
    "bucket": "your-bucket",
    "keyPrefix": "output/pdf/"
  },
  "clientRequestId": "optional-uuid-for-log-correlation"
}
```

**PDF→图像** 额外固定参数（写入 schema，阶段 1 起严格执行）：

```json
{
  "render": {
    "dpi": 150,
    "format": "png",
    "maxPages": 50,
    "pageRange": null
  }
}
```

- `pageRange` 为 `null` 表示至多转换 `maxPages` 页（从第 1 页起）；或约定 `"1-10"` 字符串，二选一并冻结。

**统一成功响应（同步）**：

```json
{
  "status": "succeeded",
  "output": {
    "bucket": "your-bucket",
    "key": "output/pdf/small_001.pdf"
  },
  "metrics": {
    "processingMs": 1234
  }
}
```

**PDF→图像** 若输出多文件：约定 `output.key` 为 **manifest JSON** 的路径，或 `output.keys` 数组 — **二选一并写入 OpenAPI**。

**统一错误体**：

```json
{
  "status": "failed",
  "error": {
    "code": "CONVERSION_TIMEOUT",
    "message": "human readable",
    "details": {}
  }
}
```

建议 `code` 枚举（初版可精简）：`INVALID_INPUT`、`OBJECT_NOT_FOUND`、`CONVERSION_FAILED`、`CONVERSION_TIMEOUT`、`NOT_IMPLEMENTED`。

### 0.3 S3 命名约定（与契约一并冻结）

```
s3://{bucket}/input/docx/{id}.docx
s3://{bucket}/input/pdf/{id}.pdf
s3://{bucket}/output/pdf/{id}.pdf
s3://{bucket}/output/images/{id}/page-%04d.png
```

- `{id}` 与 `manifest.json` 中 `id` **一致**。  
- 对象 **加密**：SSE-S3 即可（报告中写明）。  
- **禁止**在对比实验中混用「一边 S3、一边本地盘」作为持久结果层。

### 0.4 数据集 manifest（推荐格式）

**文件**：`datasets/manifest.json`，内容为 **JSON 数组**（或每行一条 JSON 的 `.jsonl`，团队择一，推荐数组便于人工编辑）。

**单条 schema**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 稳定主键，如 `docx_small_001` |
| `role` | string | 是 | `smoke` / `baseline` / `large` / `stress` |
| `format` | string | 是 | `docx` 或 `pdf` |
| `source` | string | 是 | URL 或 `corpus:superdoc-dev/docx-corpus#filter=...` |
| `license` | string | 是 | 如 `MIT`、`CC-BY-4.0` |
| `sha256` | string | 阶段 1 填 | 空字符串可先占位 `""` |
| `bytes` | number | 阶段 1 填 | 占位 `0` |
| `pages` | number \| null | 否 | PDF 用 `pdfinfo`；DOCX 可 `null` |
| `notes` | string | 否 | 表格/图片/嵌入对象等 |
| `synthetic` | boolean | 否 | 合成数据标 `true` |

**Tier A（必做）**：建议 **12–18 条**。

- `smoke`：各 1 个小 DOCX、1 个小 PDF（验证链路）。  
- `baseline`：DOCX 小/中/大至少各 1；PDF 小/中/多页至少各 1。  
- `large`：1–2 个 DOCX + 1 个 PDF，用于讨论 Lambda 时限与内存（可来自合并页或真实大文件）。  
- `stress`：1 个 **高页数** PDF（如 ≥100 页）专测 **PDF→图** 与 `maxPages` 行为。

**Tier B（可选）**：从 [docx-corpus](https://github.com/superdoc-dev/docx-corpus) 等按筛选条件随机抽样，**种子**写入 `datasets/README.md`。

### 0.5 同步 vs 异步（在阶段 0 写清决策规则）

建议在 `docs/experiment-matrix.md` 中明确：

- **同步**：输入 `bytes` ≤ 阈值（例如 5MB）且预估处理时间 < 60s（阈值可调整，需记录）。  
- **异步**：超过阈值或实现上使用 SQS/Step Functions 时，`POST` 返回 `jobId`，`GET` 轮询终态。

阶段 1 可先 **仅实现同步** + 在 OpenAPI 中预留异步 schema，但 **large 样例** 的实验目标必须与该决策一致（避免报告与实现矛盾）。

### 0.6 实验矩阵（`docs/experiment-matrix.md` 建议小节）

1. **负载形态**：冷启动（空闲 ≥30 min 后首请求）、突发（短窗口高 RPS）、阶梯升压、持续 5–10 分钟平台期。  
2. **自变量**：架构（EC2 / Lambda）、并发度、输入 `role`。  
3. **因变量**：p50/p90/p99 端到端延迟、错误率、Lambda `InitDuration`（如有）、超时次数、（可选）成本。

### 0.7 指标定义（`docs/metrics-definitions.md` 必备句）

- **端到端延迟（同步）**：从客户端 **发送 HTTP 请求** 到 **收到 200 且 body 表明 `succeeded`** 的耗时。  
- **冷启动（Lambda）**：与 CloudWatch Logs 中 **Init Duration** 对齐；实验前声明空闲时间。  
- **冷启动（EC2）**：若测容器重启后首请求，须写明 **不等于**「实例冷启动」，避免与 Proposal 措辞冲突。

### 0.8 阶段 0 完成判据（自检）

- [ ] `openapi.yaml` 可被 [Swagger Editor](https://editor.swagger.io/) 打开且无解析错误。  
- [ ] Tier A 每条均有 `id`、`role`、`format`、`source`、`license`；`sha256`/`bytes` 可暂空。  
- [ ] 队友能仅凭文档理解：**传什么 S3 key、会写什么输出 key**。  
- [ ] 实验矩阵覆盖 Proposal 中的 **冷启动、时限、伸缩/并发** 表述。

---

## 二、阶段 1：转换引擎与「单一事实来源」镜像

### 1.1 推荐技术选型（与计划一致、便于双人后续只改部署）

| 能力 | 推荐 | 许可 | 说明 |
|------|------|------|------|
| DOCX→PDF | [Gotenberg](https://github.com/gotenberg/gotenberg) 镜像内 LibreOffice | MIT | 固定 `gotenberg/gotenberg:8` 或具体 patch tag，写入 README |
| PDF→PNG | `pdftoppm`（poppler-utils） | 多为主 GPL（发行版为准） | 与 Gotenberg **同一 Dockerfile 第二阶段** 或 **同一基础镜像** 安装 |

**原则**：EC2 与 Lambda **同一 Dockerfile 构建产物**（同一 `IMAGE_TAG`），仅部署方式不同。

### 1.2 仓库目录建议（阶段 1 落地）

```
Project/
  contracts/
    openapi.yaml
  datasets/
    manifest.json
    README.md
    raw/                    # gitignore：大文件不放 Git，只放 manifest
  docs/
    experiment-matrix.md
    metrics-definitions.md
    phase0-phase1-implementation.md
  services/
    converter/
      Dockerfile
      README.md
      src/                  # 若用薄封装：调用 gotenberg 子进程或 HTTP 连 sidecar
      scripts/
        healthcheck.sh
```

若采用 **单容器内同时跑 Gotenberg + 你的 API**：注意进程管理与健康检查；更简单的是 **Gotenberg 仅作 libreoffice 模块**，你的服务用 **HTTP 调 localhost:3000** 转 DOCX→PDF，PDF→图用 **poppler CLI**（同一容器内）。

### 1.3 Dockerfile 实施要点

1. **基础镜像**：`gotenberg/gotenberg:8` 或 `FROM gotenberg/gotenberg:8` 再 `RUN apt-get update && apt-get install -y poppler-utils`（以镜像内包管理器为准，Debian/Ubuntu 系常用 `poppler-utils`）。  
2. **版本钉死**：在 `services/converter/README.md` 记录 `docker inspect` 的镜像 digest 或明确 minor tag。  
3. **字体**：若 Tier A 出现乱码/分页差异，在镜像内安装 **Noto** 或实验用固定字体集，并写入报告「字体已固定」。  
4. **非 root**（可选）：Lambda 与部分编排要求非 root，提前在阶段 1 验证。

### 1.4 应用层职责（薄封装推荐）

- 从请求体读取 `bucket/key`，用 **AWS SDK** `GetObject` 拉取到 `/tmp`（或流式）。  
- **DOCX→PDF**：调用 Gotenberg `POST /forms/libreoffice/convert` 或 `soffice --headless`（与 Gotenberg 版本一致）。  
- **PDF→图**：对 `/tmp/input.pdf` 执行 `pdftoppm -png -r 150 input.pdf outprefix`，将产物 `PutObject` 到 `output` prefix。  
- 返回统一 JSON（与 OpenAPI 一致）。

**超时**：容器内为转换设置 **与 Lambda 配置预留** 的合理上限（例如略小于 Lambda timeout），便于可预测失败类型。

### 1.5 本地验证步骤（阶段 1 退出标准）

在无 AWS 时可用 **MinIO** 或本地文件 mock；最低限度：**本地文件 + curl** 调本地起的容器。

1. 构建：`docker build -t converter:local services/converter`  
2. 运行：`docker run --rm -p 8080:8080 -e AWS_REGION=... （及测试用凭证或 LocalStack）`  
3. 将 Tier A 中 `smoke` 文件放入 S3（或挂载 volume 做「假 S3」仅开发用，正式对比前改回 S3）。  
4. 调用 `POST /v1/convert/docx-to-pdf` 与 `POST /v1/convert/pdf-to-images`，检查输出 key 与视觉/文件大小合理性。  
5. 对 **每个 Tier A 文件** 更新 `manifest.json` 的 `sha256`、`bytes`、`pages`。

**哈希命令示例**：

```bash
sha256sum datasets/raw/docx_small_001.docx
pdfinfo output.pdf | grep Pages
```

### 1.6 与阶段 0 文档的同步

- OpenAPI 若因实现微调（字段名、枚举），**改 OpenAPI 并提交**，同时在 `docs/experiment-matrix.md` 中增加一行「变更记录」。  
- `datasets/manifest.json` 中 `sha256` 全满后，在 README 中写 **固定 commit**：「数据集以此 commit 的 manifest 为准」。

### 1.7 阶段 1 完成判据（自检）

- [ ] 单一 `Dockerfile` 构建的镜像在本地跑通 **两条转换**。  
- [ ] Tier A 所有条目 `sha256`、`bytes` 已填；PDF 的 `pages` 已填。  
- [ ] `contracts/openapi.yaml` 与真实返回 **字段一致**。  
- [ ] `services/converter/README.md` 含：**构建、运行、环境变量、已知限制**（如复杂 DOCX 超时）。  

---

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-04-21 | 已落地：`contracts/openapi.yaml`、`services/converter`（Gotenberg 8 + poppler + FastAPI）、`scripts/generate_smoke_assets.py` 生成 `datasets/raw` 并填实 Tier A `manifest.json`。 |

---

## 三、单人执行顺序（建议日程）

| 天 | 任务 |
|----|------|
| 1 | 写 `openapi.yaml` 初稿 + S3 布局 + 错误模型；搭 `datasets/manifest.json` Tier A 骨架 |
| 2 | 定稿 `experiment-matrix.md`、`metrics-definitions.md`；请队友 **审阅 OpenAPI** |
| 3–4 | `Dockerfile` + 薄服务；本地打通 smoke |
| 5–6 | 跑完 Tier A，填满 manifest；修 OpenAPI 与 README |

---

## 四、参考链接（便于写报告与附录）

- Gotenberg 文档：[Convert to PDF (LibreOffice)](https://gotenberg.dev/docs/convert-with-libreoffice/convert-to-pdf)  
- 大型 DOCX 语料（子集使用）：[superdoc-dev/docx-corpus](https://github.com/superdoc-dev/docx-corpus)  
- PDF 测试集（边界）：[veraPDF/veraPDF-corpus](https://github.com/veraPDF/veraPDF-corpus)  

---

*本文档与总计划中的数据约定、阶段划分一致；阶段 2 起由队友分别对接 EC2 / Lambda 部署时，应以本文冻结的契约与镜像 tag 为准。*
