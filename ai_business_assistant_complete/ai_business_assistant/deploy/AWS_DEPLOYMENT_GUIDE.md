# 🚀 AWS Deployment Guide — AI Business Assistant

Complete step-by-step guide to deploy on AWS with EC2, RDS, S3, ECR, and GitHub Actions CI/CD.

---

## 📋 Architecture Overview

```
Internet
    │
    ▼
[Route 53] ──── DNS (optional custom domain)
    │
    ▼
[ALB - Application Load Balancer] ── Port 80/443
    │
    ▼
[EC2 - t3.medium] ── Ubuntu 22.04 + Docker
    │  FastAPI app running on port 8000
    │
    ├──► [RDS PostgreSQL] ── Private subnet (db.t3.micro)
    │
    └──► [S3 Bucket] ── File uploads & FAISS backups

[ECR] ◄── GitHub Actions ── Builds & pushes Docker image
```

---

## 🔧 Prerequisites

Install these on your local machine:

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /    # macOS
# Or: sudo apt install awscli                  # Ubuntu

# Terraform
brew install terraform       # macOS
# Or: https://developer.hashicorp.com/terraform/install

# Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-south-1), Output (json)

# Verify
aws sts get-caller-identity
```

---

## 🗝️ Step 1 — Create IAM User for Deployment

Go to **AWS Console → IAM → Users → Create User**

```
Username: ai-business-deployer
Permissions: Attach policies directly
  ✅ AmazonEC2FullAccess
  ✅ AmazonRDSFullAccess
  ✅ AmazonS3FullAccess
  ✅ AmazonECR-FullAccess
  ✅ ElasticLoadBalancingFullAccess
  ✅ AmazonVPCFullAccess
  ✅ IAMFullAccess
```

Then: **Security credentials → Create access key → Application running outside AWS**

Save the **Access Key ID** and **Secret Access Key** — you'll need them.

---

## 🔑 Step 2 — Create SSH Key Pair

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/ai-business-key -N ""

# Your public key is at: ~/.ssh/ai-business-key.pub
# Terraform will upload this automatically
```

---

## 🏗️ Step 3 — Deploy Infrastructure with Terraform

```bash
cd deploy/terraform/

# Copy and fill in your values
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars   # Fill in db_password, openai_api_key, secret_key

# Initialize Terraform
terraform init

# Preview what will be created
terraform plan

# Deploy (takes ~8 minutes)
terraform apply
# Type 'yes' when prompted

# Save the outputs!
terraform output
# ec2_public_ip  = "13.x.x.x"
# alb_dns_name   = "ai-business-assistant-alb-xxx.ap-south-1.elb.amazonaws.com"
# rds_endpoint   = "ai-business-assistant-db.xxx.ap-south-1.rds.amazonaws.com"
# s3_bucket_name = "ai-business-assistant-assets-xxxx"
```

**What Terraform creates:**
- VPC with public + private subnets across 2 AZs
- EC2 t3.medium in public subnet (with Docker pre-installed via user_data)
- RDS PostgreSQL 16 in private subnet
- S3 bucket with versioning and encryption
- Application Load Balancer
- Security groups with least-privilege rules
- IAM role for EC2 → S3 access
- Elastic IP for stable public address

---

## 🐳 Step 4 — Setup AWS ECR (Container Registry)

```bash
# Run the ECR setup script
export AWS_REGION=ap-south-1
bash deploy/setup_ecr.sh

# Output will look like:
# ECR URI: 123456789.dkr.ecr.ap-south-1.amazonaws.com/ai-business-assistant
```

---

## 🔐 Step 5 — Add GitHub Secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret Name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | From Step 1 |
| `AWS_SECRET_ACCESS_KEY` | From Step 1 |
| `EC2_HOST` | EC2 public IP from `terraform output` |
| `EC2_SSH_KEY` | Contents of `~/.ssh/ai-business-key` (private key) |

```bash
# To get your private key content:
cat ~/.ssh/ai-business-key
# Copy the entire output including -----BEGIN RSA PRIVATE KEY-----
```

---

## 🚢 Step 6 — First Manual Deployment

Before CI/CD kicks in, do the first deployment manually:

```bash
# Get your ECR URI
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/ai-business-assistant"

# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin $ECR_URI

# Build and push
docker build -t $ECR_URI:latest .
docker push $ECR_URI:latest

# SSH into EC2
ssh -i ~/.ssh/ai-business-key ubuntu@<EC2_PUBLIC_IP>

# On EC2: pull and start the app
cd /opt/ai-business-assistant
cat docker-compose.yml     # Verify .env and image are set correctly

# Pull image (EC2 has IAM role, so no login needed)
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin $ECR_URI

# Update docker-compose image
sed -i "s|image: .*|image: $ECR_URI:latest|" docker-compose.yml

# Start
docker compose up -d

# Check logs
docker compose logs -f
```

---

## 🔄 Step 7 — CI/CD with GitHub Actions

After Step 5 and 6, every push to `main` will automatically:

1. ✅ Run tests
2. 🐳 Build Docker image → push to ECR
3. 🚀 SSH into EC2 → pull new image → rolling restart
4. 🏥 Health check to confirm deployment

```bash
# Trigger a deployment
git add .
git commit -m "feat: my new feature"
git push origin main

# Watch it deploy:
# GitHub → Actions tab → "Deploy to AWS"
```

---

## 🌐 Step 8 — Custom Domain + SSL (Optional)

### If you have a domain:

```bash
# SSH into EC2
ssh -i ~/.ssh/ai-business-key ubuntu@<EC2_PUBLIC_IP>

# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Configure Nginx
sudo nano /etc/nginx/sites-available/ai-business-assistant
```

Paste:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    proxy_read_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ai-business-assistant /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificate (free via Let's Encrypt)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Done! Your app is now at https://yourdomain.com
```

### Point your domain to AWS:
- In Route 53 (or your DNS provider), add an **A record**:
  - Name: `@` (or `yourdomain.com`)
  - Value: ALB DNS name (from `terraform output alb_dns_name`)
  - OR: EC2 Elastic IP

---

## 📊 Step 9 — Monitoring & Logs

```bash
# View app logs
ssh -i ~/.ssh/ai-business-key ubuntu@<EC2_PUBLIC_IP>
docker compose logs -f --tail=100

# Check resource usage
docker stats

# Check disk space
df -h

# EC2 system logs
sudo journalctl -u ai-business-assistant -f
```

### CloudWatch (optional - AWS native monitoring):
```bash
# Install CloudWatch agent on EC2
sudo apt install amazon-cloudwatch-agent -y
# Configure to ship Docker logs to CloudWatch
# AWS Console → CloudWatch → Log groups → /ai-business-assistant
```

---

## 💰 AWS Cost Estimate (ap-south-1 Mumbai)

| Service | Spec | ~Monthly Cost |
|---|---|---|
| EC2 t3.medium | 2 vCPU, 4GB RAM | ~$30 |
| RDS db.t3.micro | PostgreSQL 16 | ~$15 |
| ALB | Per hour + LCU | ~$20 |
| S3 | 10GB storage | ~$0.25 |
| ECR | 1GB storage | ~$0.10 |
| Data Transfer | ~10GB/mo | ~$1 |
| **Total** | | **~$66/month** |

**To reduce costs:**
- Use **EC2 t3.small** (~$15/mo) for low traffic
- Use **RDS db.t3.micro** with single-AZ
- Skip ALB and use Nginx directly (~$20 savings)
- Use **Spot Instances** for non-prod environments

---

## 🧹 Cleanup (Destroy Everything)

```bash
# ⚠️  WARNING: This deletes ALL resources permanently
cd deploy/terraform/
terraform destroy
# Type 'yes' to confirm

# Also delete ECR images
aws ecr delete-repository \
  --repository-name ai-business-assistant \
  --region ap-south-1 \
  --force
```

---

## 🔒 Security Checklist

- [ ] RDS is in private subnet (no public access)
- [ ] EC2 SSH restricted to your IP in Security Group
- [ ] `.env` file NOT committed to git
- [ ] `terraform.tfvars` NOT committed to git  
- [ ] Strong `SECRET_KEY` and `DB_PASSWORD`
- [ ] S3 bucket has public access blocked
- [ ] ECR image scanning enabled
- [ ] IAM user has minimum required permissions

---

## 🆘 Troubleshooting

**App not starting:**
```bash
docker compose logs api
# Check for missing env vars or DB connection errors
```

**Can't connect to RDS:**
```bash
# Verify security group allows EC2 → RDS on port 5432
# Check DATABASE_URL in .env uses RDS endpoint, not localhost
```

**ECR push fails:**
```bash
# Re-authenticate
aws ecr get-login-password --region ap-south-1 | docker login ...
```

**GitHub Actions deploy fails:**
```bash
# Check EC2_SSH_KEY secret includes full key with header/footer
# Verify EC2_HOST is public IP, not private
```
