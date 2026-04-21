# 数据集（Group 259）

## 约定

- 清单文件：[manifest.json](manifest.json)（Tier A 已由 `scripts/generate_smoke_assets.py` 填实 `sha256` / `bytes` / `pages`）。
- 重新生成合成数据：在项目根目录执行 `pip install -r scripts/requirements.txt` 后运行 `python scripts/generate_smoke_assets.py`。
- 大文件不放 Git：本地或 CI 将原件放在 `datasets/raw/`，该目录已 `.gitignore`。
- S3 键与 `id` 对齐，见 [contracts/openapi.yaml](../contracts/openapi.yaml) 与项目 `phase0-phase1-implementation.md`。

## Tier A 来源说明

| 类型 | 策略 |
|------|------|
| smoke / baseline 小文件 | 仓库内合成或课程自备；许可标注 `synthetic` 或 `MIT`（若来自模板）。 |
| 真实 DOCX 多样性 | 可选从 [superdoc-dev/docx-corpus](https://github.com/superdoc-dev/docx-corpus) 按 API manifest 下载子集（MIT）；勿提交隐私文档。 |
| PDF 边界样例 | 可选从 [veraPDF/veraPDF-corpus](https://github.com/veraPDF/veraPDF-corpus)（CC BY 4.0）抽取少量文件。 |

## Tier B（可选）

- 随机抽样种子（占位）：`RANDOM_SEED=5296`（写入报告与附录时再确认）。
- 从 docx-corpus 筛选条件示例：`type=technical&lang=en&min_confidence=0.8`。

## 伦理与脱敏

- 网络语料仅用于研究子集；对比实验使用固定 `manifest` 中的对象与哈希，便于复现。
