# Group 259：阶段 0–1 交接说明与阶段 2 对齐（给队友）
本文档用于 **两人对齐**：已完成的契约与镜像、双 AWS 学生账号的注意点、进入阶段 2（EC2 / Serverless 部署与压测）前需共同填写的约定。
---
## 1. 项目目标（一句话）
在同一套 **DOCX→PDF**（Gotenberg/LibreOffice）与 **PDF→PNG**（poppler `pdftoppm`）逻辑下，将 **同一 Docker 镜像** 分别部署在 **常驻 EC2** 与 **Lambda + API Gateway**，对比冷启动、时限、伸缩与并发等架构差异（见小组 Proposal）。
---
## 2. 两个 AWS 学生账号可以吗？
**可以**：你们各自保留学生账号与各自 **$50** 额度没有问题。
**但要注意公平对比**：
| 若采用 | 影响 | 建议 |
|--------|------|------|
| **EC2 与 Lambda 分属两个独立账户** | 网络路径、配额、底层噪声可能不同；S3 默认不能让对方直接读 | 报告中需专设「账户/跨账户配置」说明；对象需 **跨账户 IAM** 或 **双份上传 + 相同 SHA256**（见 `datasets/manifest.json`） |
| **对比实验在同一账户内完成** | 控制变量最干净，复现最简单 | **推荐**：选定 **一个主账户** 承载共享 S3、ECR、以及两条部署；另一人通过 **IAM 用户/协作权限** 操作主账户资源（个人额度仍可用于各自试错，正式数据以主账户为准） |
**结论**：额度可以两人各 50$；**至少**让 **共享 S3 与同一 region 下的对比部署** 落在同一账户，会显著减少报告里需要解释的变量。

---

## 3. 阶段 0–1 已完成交付物（仓库内路径）

**镜像与阶段 2 用法（纯文本，便于转发）**：见同目录 [group259-docker-image-handoff.txt](group259-docker-image-handoff.txt)。

| 类别 | 路径 | 说明 |
|------|------|------|
| API 契约 | [contracts/openapi.yaml](../contracts/openapi.yaml) | OpenAPI 3 |
| 示例 HTTP | [contracts/examples/sample-requests.http](../contracts/examples/sample-requests.http) | 联调模板 |
| 数据清单 | [datasets/manifest.json](../datasets/manifest.json) | Tier A：`sha256` / `bytes` / `pages` 已由脚本填实 |
| 数据说明 | [datasets/README.md](../datasets/README.md) | 再生合成数据：`pip install -r scripts/requirements.txt` 后 `python scripts/generate_smoke_assets.py` |
| 生成脚本 | [scripts/generate_smoke_assets.py](../scripts/generate_smoke_assets.py) | 合成 DOCX/PDF 至 `datasets/raw/`（目录 gitignore） |
| 实验矩阵 | [docs/experiment-matrix.md](experiment-matrix.md) | 负载形态、API GW 边界 |
| 指标口径 | [docs/metrics-definitions.md](metrics-definitions.md) | p50/p90/p99、冷启动定义 |
| 阶段 0/1 细则 | [docs/phase0-phase1-implementation.md](phase0-phase1-implementation.md) | 原始实施步骤与变更记录 |
| 转换服务 | [services/converter/](../services/converter/) | `Dockerfile`、`entrypoint.sh`、`src/main.py`、`README.md` |

---

## 4. Docker 镜像与本地验证
```bash
cd services/converter
docker build -t group259-converter:local .
docker run --rm --name g259 -p 8080:8080 -p 3000:3000 \
  -e AWS_REGION=<your-region> \
  group259-converter:local
```
- **API**：`curl http://127.0.0.1:8080/health` 期望 `{"status":"ok"}`  
- **Gotenberg**：`curl http://127.0.0.1:3000/health` 期望含 `libreoffice` 等状态  
**Windows 检出 CRLF**：`Dockerfile` 构建阶段已对 `entrypoint.sh` 执行 `sed` 去掉 `\r`；仓库 [.gitattributes](../.gitattributes) 对 `*.sh` 使用 LF。详见 [services/converter/README.md](../services/converter/README.md)。
**转换接口**依赖 **S3 凭证**（环境变量、实例元数据或挂载 `~/.aws`），需将 `manifest` 中对象按约定上传到 `input/docx/`、`input/pdf/` 等前缀后再调用 API。
---
## 5. 阶段 2 关键架构约束（务必对齐）
1. **同一镜像**：EC2 与 Lambda 使用 **相同 tag**，并在报告中记录 **digest**（`docker inspect --format='{{index .RepoDigests 0}}' ...`）。  
2. **API Gateway 同步**：经 API GW 的 Lambda 同步集成约 **29s**；`large` / `stress` 类输入需 **异步 job**、Step Functions，或 **直连测量路径**（必须在报告中写清口径）。  
3. **S3 约定**：输入/输出仅用 S3，键与 `manifest` 中 `id` 一致；见 OpenAPI 与 [phase0-phase1-implementation.md](phase0-phase1-implementation.md) 中的前缀约定。
---
## 6. 与队友对齐表（复制到会议记录或填好后提交 PR 描述）
| 项 | 约定值（待填写） |
|----|------------------|
| AWS 策略 | 单主账户 / 双账户（若双账户：跨账户访问与对象哈希如何对齐） |
| Region | 例如 `ap-east-1`（**两人部署一致**） |
| S3 Bucket | |
| 对象前缀 | `input/docx/`、`input/pdf/`、`output/pdf/`、`output/images/{id}/` |
| ECR 仓库名 | |
| 镜像 tag / digest | |
| EC2 负责人 | |
| EC2 实例类型 | |
| ALB 空闲超时（秒） | |
| Serverless 负责人 | |
| Lambda 内存（MB） | |
| Lambda 超时（秒） | |
| Lambda /tmp（MB） | |
| 是否 VPC | |
| API 类型 | HTTP API / REST |
| 压测工具 | k6 / Locust（**版本**） |
| 压测脚本路径（仓库内） | |
| 公开 GitHub 仓库 URL | |
---
## 7. 课程交付提醒（CS5296）
- **最终报告**（含 Group ID、IEEE 参考文献、**Artifact 附录**）：按课程说明页数与截止时间提交 PDF。  
- **软件制品**：**公开** GitHub；附录需可复现（构建、输入、期望输出）；**多成员、跨时间段** commit。  
- **演示视频**：英文、≤10 分钟，YouTube 或 bilibili **公开** 链接提交 Canvas。  
- **学术诚信**：报告勿用 LLM 代写（按课程要求）。
---