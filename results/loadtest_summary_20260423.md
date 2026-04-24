# 压测摘要（本地执行，2026-04-23）

## 前提

- **S3** `cs5296-project` 经 **EC2 实例角色** 列出 `input/docx/`：当前仅有 **`docx_smoke_001.docx`**。请求体见项目根目录 `.curl-body-docx-pdf.json`。
- **本地 AWS CLI**（voclabs 用户）对该桶为 **ListBucket 显式拒绝**，无法在本文环境用 CLI 列桶；与 Lambda/EC2 任务角色无关。
- **EC2 公网** `98.93.115.249:8080` 从当前网络 **连接超时**（安全组未对公网放行 8080 为预期情况）。EC2 压测在 **实例内** 对 `127.0.0.1:8080` 执行。
- **Lambda Function URL**：`https://w7tivllplqmgmmse6uqknsnn4m0dkosp.lambda-url.us-east-1.on.aws/v1/convert/docx-to-pdf`

## Lambda（客户端测，PowerShell Invoke-RestMethod）

| 场景 | 说明 |
|------|------|
| 顺序 5 次 | `results/loadtest_lambda_seq_20260423_160357.json`；`clientMs` 约 **1400–2300 ms**（温机后多数约 1.4–1.5 s），`processingMs` 约 **880–960 ms** |
| 并发 3 | `results/loadtest_lambda_par3_*.json`；同发 3 请求，**clientMs** 约 **2400 / 4700 / 8800 ms**，**processingMs** 约 **938 / 1855 / 5517 ms**（并发下尾延迟与单请求处理时间上升，符合竞争） |

## EC2（实例内 curl，脚本 `benchmarks/ec2-local-curl-loop.sh`）

| seq | time_total_sec (curl) | http |
|-----|------------------------|------|
| 1 | 1.982 | 200 |
| 2 | 0.940 | 200 |
| 3 | 0.958 | 200 |
| 4 | 0.862 | 200 |
| 5 | 0.862 | 200 |

首包略长，之后约 **0.86–0.96 s**（同机、同桶、小文件，无冷启容器时很稳）。

## 复现

1. 更新 `.curl-body-docx-pdf.json` 中 S3 key 与桶内真实对象一致。
2. Lambda：在项目根 PowerShell 中可复用已跑过的顺序/并发 one-liner（或见 `results/*.json` 旁注）。
3. EC2：  
   `scp .curl-body-docx-pdf.json ubuntu@<公网IP>:/tmp/body-docx-pdf.json`  
   `scp benchmarks/ec2-local-curl-loop.sh ubuntu@<公网IP>:/tmp/`  
   `ssh ubuntu@<公网IP> "chmod +x /tmp/ec2-local-curl-loop.sh && bash /tmp/ec2-local-curl-loop.sh /tmp/body-docx-pdf.json"`

## 外网直打 EC2 转换端口

在 **安全组** 中为你的公网 IP 放行 **TCP 8080**（或经 ALB 只开 80/443）后，可将 `BASE_EC2` 设为 `http://<公网IP>:8080` 在本机用同一 JSON 对 EC2 做与 Lambda 对称的 `curl`/`k6` 压测。
