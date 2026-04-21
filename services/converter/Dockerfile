# Single image for EC2 and Lambda (phase 2): Gotenberg 8 + poppler + FastAPI wrapper
FROM gotenberg/gotenberg:8

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
# Strip Windows CRLF so /bin/bash is found when building on Windows checkout
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8080 3000

ENTRYPOINT ["/entrypoint.sh"]
