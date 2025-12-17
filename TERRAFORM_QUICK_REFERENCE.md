# Quick Reference: Terraform Setup

## 🎯 What You Have

### 3 Core Infrastructure Components

| Component | Purpose | Output Variable |
|-----------|---------|------------------|
| **Gateway Role** | Create and manage gateways | `GATEWAY_ROLE_ARN` |
| **Credentials Role** | Manage API key credential providers | `CREDENTIALS_ROLE_ARN` |
| **S3 Bucket** | Store OpenAPI specs | `S3_BUCKET_NAME` |

---

## ⚡ Quick Start

```bash
cd terraform
terraform init
terraform apply
```

---

## 📝 .env File Setup

### Option 1: Automatic (Recommended)
```bash
# This outputs your entire .env content ready to copy-paste
terraform output env_file_content
```

### Option 2: Manual
```bash
export GATEWAY_ROLE_ARN=$(terraform output -raw gateway_role_arn)
export CREDENTIALS_ROLE_ARN=$(terraform output -raw credentials_role_arn)
export S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)

# Add to .env file
echo "GATEWAY_ROLE_ARN=$GATEWAY_ROLE_ARN" >> .env
echo "CREDENTIALS_ROLE_ARN=$CREDENTIALS_ROLE_ARN" >> .env
echo "S3_BUCKET_NAME=$S3_BUCKET_NAME" >> .env
```

---

## 🔍 Verify Deployment

```bash
# Check all outputs
terraform output

# Check specific resources in AWS
aws iam get-role --role-name test-agentcore-lgateway-role-demo
aws iam get-role --role-name test-agentcore-credentials-role-demo
aws s3 ls | grep agentcore
```

---

## 📋 Files Modified

- `terraform/main.tf` - Added S3 bucket, updated outputs
- `terraform/variables.tf` - Added `s3_bucket_name` variable
- `TERRAFORM_COMPLETE_SETUP.md` - Comprehensive documentation

---

## 🚀 Next Steps

1. **Deploy Terraform**
   ```bash
   terraform apply
   ```

2. **Get Environment Variables**
   ```bash
   terraform output env_file_content
   ```

3. **Update .env File**
   ```bash
   # Copy output from above into your .env
   ```

4. **Verify in Your Application**
   - The Gateway Role ARN is ready for creating gateways
   - The Credentials Role ARN is ready for creating credential providers
   - The S3 Bucket is ready for storing OpenAPI specs

---

## 💾 Files in Terraform Directory

```
terraform/
├── main.tf                 ← All resource definitions
├── variables.tf            ← Variable definitions
├── terraform.tfstate       ← State file (don't commit)
├── terraform.tfstate.backup ← Backup state (don't commit)
├── prod.tfvars            ← Production overrides (optional)
├── dev.tfvars             ← Dev overrides (optional)
├── README.md              ← Setup instructions
└── .gitignore             ← Should exclude .tfstate files
```

---

## 🎓 Understanding the Setup

### Gateway Role Flow
```
Your Application
    ↓
AWS CLI / SDK (with Gateway Role ARN)
    ↓
Bedrock AgentCore Control API
    ↓
Creates/Manages Gateways
```

### Credentials Role Flow
```
Your Application
    ↓
Credentials Service (creates API key provider)
    ↓
Bedrock AgentCore Control API
    ↓
Creates Credential Provider
    ↓
Stores in Secrets Manager
```

### S3 Bucket Flow
```
Your Application
    ↓
Upload OpenAPI Spec to S3
    ↓
S3 Bucket (with versioning)
    ↓
Reference in Gateway Target Creation
    ↓
s3://agentcore-gateway-specs-{account}-{region}/specs/openapi.json
```

---

## ❓ FAQ

**Q: What if I want to use different names?**
```bash
terraform apply \
  -var="gateway_role_name=my-gateway-role" \
  -var="credentials_role_name=my-creds-role" \
  -var="s3_bucket_name=my-specs-bucket"
```

**Q: How do I use different settings for dev/prod?**
```bash
# Development
terraform apply -var-file="dev.tfvars"

# Production
terraform apply -var-file="prod.tfvars"
```

**Q: Can I delete just one component?**
```bash
# Delete only the S3 bucket
terraform destroy -target=aws_s3_bucket.gateway_specs_bucket

# Delete only gateway role
terraform destroy -target=aws_iam_role.gateway_role
```

**Q: Where should I store the .env file?**
- Add `*.env` to `.gitignore`
- Keep it locally for development
- Use AWS Secrets Manager or environment variables for deployed applications

---

## ✅ Success Indicators

After running `terraform apply`, you should see:

```
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.

Outputs:
gateway_role_arn = "arn:aws:iam::123456789012:role/test-agentcore-lgateway-role-demo"
gateway_role_name = "test-agentcore-lgateway-role-demo"
credentials_role_arn = "arn:aws:iam::123456789012:role/test-agentcore-credentials-role-demo"
credentials_role_name = "test-agentcore-credentials-role-demo"
s3_bucket_name = "agentcore-gateway-specs-123456789012-us-east-1"
s3_bucket_arn = "arn:aws:s3:::agentcore-gateway-specs-123456789012-us-east-1"
env_file_content = "GATEWAY_ROLE_ARN=arn:aws:iam::123456789012:role/test-agentcore-lgateway-role-demo\nCREDENTIALS_ROLE_ARN=arn:aws:iam::123456789012:role/test-agentcore-credentials-role-demo\nS3_BUCKET_NAME=agentcore-gateway-specs-123456789012-us-east-1"
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| S3 bucket name taken | Change `s3_bucket_name` variable (must be globally unique) |
| IAM role already exists | Change `gateway_role_name` or `credentials_role_name` |
| AWS credentials error | Run `aws configure` and set credentials |
| State file conflicts | Run `terraform init` to reinitialize |


