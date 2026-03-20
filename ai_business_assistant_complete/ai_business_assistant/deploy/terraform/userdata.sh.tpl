#!/bin/bash
# EC2 User Data — runs once on first boot
# Installs Docker, pulls app, writes .env, starts service

set -e
exec > /var/log/userdata.log 2>&1

echo "=== Starting AI Business Assistant bootstrap ==="

# Update system
apt-get update -y && apt-get upgrade -y

# Install Docker
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker ubuntu

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
apt-get install -y unzip
unzip -q awscliv2.zip && ./aws/install
rm -rf aws awscliv2.zip

# Setup app directory
APP_DIR="/opt/ai-business-assistant"
mkdir -p $APP_DIR
chown ubuntu:ubuntu $APP_DIR

# Write .env file using Terraform template variables
cat > $APP_DIR/.env <<ENV
OPENAI_API_KEY=${openai_key}
OPENAI_MODEL=gpt-4o-mini
TEMPERATURE=0.7
DATABASE_URL=${db_url}
SECRET_KEY=${secret_key}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
DEBUG=False
AWS_S3_BUCKET=${s3_bucket}
ENV

# Write production docker-compose (uses external RDS, not local postgres)
cat > $APP_DIR/docker-compose.yml <<COMPOSE
version: "3.9"
services:
  api:
    image: ai-business-assistant:latest
    container_name: ai-business-assistant
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./static:/app/static
    restart: unless-stopped
COMPOSE

# Setup systemd service
cat > /etc/systemd/system/ai-business-assistant.service <<SERVICE
[Unit]
Description=AI Business Assistant
Requires=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=120
Restart=on-failure
User=ubuntu

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable ai-business-assistant

echo "=== Bootstrap complete! Deploy your Docker image to start the app ==="
