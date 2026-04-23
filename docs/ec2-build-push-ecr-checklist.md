# EC2: build, tag, and push the converter image to ECR

**Use case**: On an EC2 instance in the **same AWS Region** as the ECR repository (e.g. `us-east-1`), clone this repo, build the converter image, and push to a **private** ECR repository. Large images often upload more reliably from same-region EC2 than from a home network across regions.

**Prerequisites (verify once)**:

- EC2 and the ECR repository are in the **same Region** (e.g. `us-east-1`).
- Security group allows **inbound SSH (port 22)** (or your chosen access).
- The EC2 instance has an **IAM instance profile** with permissions to **push** to the target ECR repository (replace `ACCOUNT_ID` and `REPO_NAME` in ARNs):
  - Simpler: `AmazonEC2ContainerRegistryFullAccess` (if your course allows), or
  - Scoped: `ecr:GetAuthorizationToken` and on `arn:aws:ecr:us-east-1:ACCOUNT_ID:repository/REPO_NAME` allow `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload` (and related read APIs as required).
- Access to the Git remote for `git clone` (if the repo is private, use an HTTPS token or SSH deploy key).

Set variables on the instance (edit `ACCOUNT_ID` / `REPO_NAME` as needed):

```bash
export AWS_REGION="us-east-1"
export ACCOUNT_ID="161748405735"
export ECR_URL="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
export REPO_NAME="cs5296-project"
export IMAGE_TAG="latest"   # or e.g. v0.1.0
```

---

## Amazon Linux 2023

```bash
# 1) Update and install Git + Docker
sudo dnf -y update
sudo dnf -y install git docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# To use `docker` without sudo in a new shell: newgrp docker
# Or prefix commands below with: sudo docker ...

# 2) (Optional) AWS CLI—often present on AL2023
aws --version || sudo dnf -y install awscli

# 3) Clone the repo (replace URL with your fork if needed)
cd ~
git clone https://github.com/singletaps/cs5296project.git
cd cs5296project/services/converter

# 4) Build (default target = ec2: Gotenberg + API)
sudo docker build -t ${REPO_NAME}:${IMAGE_TAG} .

# 5) Log in to ECR and tag
aws ecr get-login-password --region ${AWS_REGION} | sudo docker login --username AWS --password-stdin ${ECR_URL}
sudo docker tag ${REPO_NAME}:${IMAGE_TAG} ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}

# 6) Push
sudo docker push ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}
```

---

## Ubuntu 22.04

```bash
# 1) Install tools
sudo apt-get update
sudo apt-get install -y git ca-certificates curl docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Or: newgrp docker; or use sudo docker below

# 2) (Optional) Install AWS CLI v2 per AWS docs, or: sudo apt install awscli

# 3) Clone
cd ~
git clone https://github.com/singletaps/cs5296project.git
cd cs5296project/services/converter

# 4) Build
sudo docker build -t ${REPO_NAME}:${IMAGE_TAG} .

# 5) ECR login + tag
aws ecr get-login-password --region ${AWS_REGION} | sudo docker login --username AWS --password-stdin ${ECR_URL}
sudo docker tag ${REPO_NAME}:${IMAGE_TAG} ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}

# 6) Push
sudo docker push ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}
```

---

## Lambda image (optional)

For **AWS Lambda (container) + [Lambda Web Adapter](https://aws.github.io/aws-lambda-web-adapter/getting-started/docker-images.html)**, build the `lambda` stage and push a separate tag (see [lambda-container-deploy.md](./lambda-container-deploy.md)):

```bash
cd ~/cs5296project/services/converter
sudo docker build --target lambda -t ${REPO_NAME}:lambda .
sudo docker tag ${REPO_NAME}:lambda ${ECR_URL}/${REPO_NAME}:lambda
aws ecr get-login-password --region ${AWS_REGION} | sudo docker login --username AWS --password-stdin ${ECR_URL}
sudo docker push ${ECR_URL}/${REPO_NAME}:lambda
```

---

## Optional: tiny ECR smoke test (separate context directory)

To verify ECR write permissions with a very small custom build:

```bash
cd ~/cs5296project/services/converter/smoke-ecr-test
sudo docker build -t cs5296-local-smoke:latest .
sudo docker tag cs5296-local-smoke:latest ${ECR_URL}/${REPO_NAME}:local-smoke
aws ecr get-login-password --region ${AWS_REGION} | sudo docker login --username AWS --password-stdin ${ECR_URL}
sudo docker push ${ECR_URL}/${REPO_NAME}:local-smoke
```

---

## Verify

```bash
aws ecr describe-images --repository-name ${REPO_NAME} --region ${AWS_REGION} --output table
```

On another host that can reach ECR (after `docker login`):

```bash
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URL}
docker pull ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}
```

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `Unable to locate credentials` | No IAM role on the instance, or role lacks `ecr:GetAuthorizationToken`. Do not rely on long-term keys copied to EC2; prefer the instance role. |
| `Repository ... does not exist` | Create the private repository in the ECR console first. |
| `AccessDenied` on push | Instance role missing push permissions for that repository. |
| `docker: command not found` | Install and start Docker (`sudo systemctl start docker`). |
| Build or pull time-outs | Instance must reach the internet (NAT or public IP + allow outbound) for `docker.io` and Git. |

---

## Learner Lab note

- Short-lived keys from the **Learner Lab** console are for **your laptop** (`aws configure` + `docker push` from your PC).
- On **EC2**, prefer the **instance IAM role** for `aws ecr get-login-password` (no long-lived secrets on disk).

If your school forbids a standalone EC2 with an IAM role, use whatever build environment the course provides.

Edit `ACCOUNT_ID`, `REPO_NAME`, and the `git clone` URL to match your team’s repository.
