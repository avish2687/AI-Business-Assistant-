#!/bin/bash
# =============================================================================
# Setup AWS ECR Repository for Docker images
# Run locally ONCE before first deployment
# Usage: AWS_REGION=ap-south-1 bash setup_ecr.sh
# =============================================================================

set -e

REGION=${AWS_REGION:-"ap-south-1"}
APP_NAME="ai-business-assistant"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Setting up ECR in region: $REGION"
echo "AWS Account ID: $ACCOUNT_ID"

# Create ECR repository
aws ecr create-repository \
    --repository-name $APP_NAME \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    2>/dev/null || echo "Repository already exists"

# Set lifecycle policy (keep last 10 images only)
aws ecr put-lifecycle-policy \
    --repository-name $APP_NAME \
    --region $REGION \
    --lifecycle-policy-text '{
      "rules": [{
        "rulePriority": 1,
        "description": "Keep last 10 images",
        "selection": {
          "tagStatus": "any",
          "countType": "imageCountMoreThan",
          "countNumber": 10
        },
        "action": { "type": "expire" }
      }]
    }'

ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME"

echo ""
echo "✅ ECR Setup complete!"
echo ""
echo "ECR URI: $ECR_URI"
echo ""
echo "Add this to GitHub Secrets:"
echo "  AWS_ACCESS_KEY_ID     = <your-key>"
echo "  AWS_SECRET_ACCESS_KEY = <your-secret>"
echo "  EC2_HOST              = <your-ec2-public-ip>"
echo "  EC2_SSH_KEY           = <contents of your .pem file>"
echo ""
echo "To push manually:"
echo "  aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI"
echo "  docker build -t $ECR_URI:latest ."
echo "  docker push $ECR_URI:latest"
