# syntax=docker/dockerfile:1
# Stages: app (shared) -> lambda (API GW/Lambda) -> ec2 (default, Gotenberg+API)
# Default `docker build -t myimg .` builds the LAST stage: ec2 (unchanged EC2/ALB behavior).
# Lambda:  docker build --target lambda -t myimg:lambda .

# ========== app: shared layers (inherits gotenberg:8 until ENTRYPOINT cleared in a child stage) ==========
FROM gotenberg/gotenberg:8 AS app

USER root

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl \
    python3 \
    python3-venv \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m venv /opt/venv \
  && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

COPY src/ ./src/
COPY entrypoint.sh /entrypoint.sh
COPY entrypoint-lambda.sh /entrypoint-lambda.sh
# Strip Windows CRLF so /bin/bash is found when building on Windows checkout
RUN sed -i 's/\r$//' /entrypoint.sh /entrypoint-lambda.sh \
  && chmod +x /entrypoint.sh /entrypoint-lambda.sh

# ========== lambda: LWA; RIC ships with the adapter (non-AWS base images) ==========
FROM app AS lambda
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.0 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=8080
ENV AWS_LWA_READINESS_CHECK_PATH=/health
EXPOSE 8080
# Drop gotenberg's inherited ENTRYPOINT; LWA spawns the process from CMD
ENTRYPOINT []
CMD ["/bin/bash", "/entrypoint-lambda.sh"]

# ========== ec2: default final stage (unchanged) ==========
FROM app AS ec2
EXPOSE 8080 3000
ENTRYPOINT ["/entrypoint.sh"]
