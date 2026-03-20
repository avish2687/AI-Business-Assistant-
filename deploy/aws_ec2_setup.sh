#!/bin/bash
# =============================================================================
# AWS EC2 Setup Script for AI Business Assistant
# Run this on a fresh Ubuntu 22.04 EC2 instance
# Usage: bash aws_ec2_setup.sh
# =============================================================================

set -e  # Exit on any error

echo "============================================="
echo "  AI Business Assistant - AWS EC2 Setup"
echo "============================================="

# ── 1. System Update ──────────────────────────────────────────────────────────
echo "[1/8] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

# ── 2. Install Docker ─────────────────────────────────────────────────────────
echo "[2/8] Installing Docker..."
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker

# ── 3. Install AWS CLI ────────────────────────────────────────────────────────
echo "[3/8] Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt-get install -y unzip
unzip -q awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip
aws --version

# ── 4. Install Nginx (reverse proxy) ─────────────────────────────────────────
echo "[4/8] Installing Nginx..."
sudo apt-get install -y nginx
sudo systemctl enable nginx

# ── 5. Install Certbot (SSL) ──────────────────────────────────────────────────
echo "[5/8] Installing Certbot for SSL..."
sudo apt-get install -y certbot python3-certbot-nginx

# ── 6. Clone / Pull App ───────────────────────────────────────────────────────
echo "[6/8] Setting up application directory..."
APP_DIR="/opt/ai-business-assistant"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# If git repo exists, clone it; otherwise copy files
if [ -n "$GIT_REPO_URL" ]; then
    git clone $GIT_REPO_URL $APP_DIR
else
    echo "  -> Set GIT_REPO_URL env var to clone your repo automatically"
    echo "  -> Or manually copy your project to $APP_DIR"
fi

# ── 7. Configure Nginx ────────────────────────────────────────────────────────
echo "[7/8] Configuring Nginx reverse proxy..."
DOMAIN=${DOMAIN:-"your-domain.com"}

sudo tee /etc/nginx/sites-available/ai-business-assistant > /dev/null <<NGINX
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # Increase timeouts for long AI requests
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;

    # Static files
    location /static/ {
        alias $APP_DIR/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # API proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support (for future features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/ai-business-assistant /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# ── 8. Setup systemd service ──────────────────────────────────────────────────
echo "[8/8] Creating systemd service for auto-restart..."
sudo tee /etc/systemd/system/ai-business-assistant.service > /dev/null <<SERVICE
[Unit]
Description=AI Business Assistant (Docker Compose)
Requires=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable ai-business-assistant

echo ""
echo "============================================="
echo "  EC2 Setup Complete!"
echo "============================================="
echo ""
echo "Next steps:"
echo "  1. Copy your project to: $APP_DIR"
echo "  2. Create .env file:     $APP_DIR/.env"
echo "  3. Start app:            sudo systemctl start ai-business-assistant"
echo "  4. Enable SSL:           sudo certbot --nginx -d $DOMAIN"
echo ""
