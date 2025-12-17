# AgentCore Gateway Terraform Complete Setup

## Overview
This Terraform configuration creates a complete infrastructure for AgentCore Gateway with:
1. **Gateway Role** - Manages gateway creation and operations
2. **Credentials Role** - Manages API key credential providers
3. **S3 Bucket** - Stores OpenAPI specs and tool configurations

---

## 📋 Components

### 1. Gateway Role (`gateway_role`)
**Purpose:** Create and manage Bedrock AgentCore gateways

**Trust Relationship:**
- Trusted by: `bedrock-agentcore.amazonaws.com`

**Permissions:**
```
Bedrock AgentCore Control:
├── bedrock-agentcore-control:*
├── bedrock-agentcore:GetWorkloadAccessToken
├── bedrock-agentcore:InvokeCredentialProvider
└── bedrock-agentcore:GetResourceApiKey

S3 Operations:
├── s3:GetObject
├── s3:PutObject
└── s3:ListBucket

Other Services:
├── iam:PassRole
├── cognito-idp:*
├── sts:GetCallerIdentity
└── secretsmanager:GetSecretValue
```

**Configuration:**
```hcl
variable "gateway_role_name" {
  default = "test-agentcore-lgateway-role-demo"
}
```

---

### 2. Credentials Role (`credentials_role`)
**Purpose:** Create and manage API key credential providers for gateway targets

**Trust Relationship:**
- Trusted by: `bedrock-agentcore.amazonaws.com`

**Permissions:**
```
Credential Provider Operations:
├── bedrock-agentcore-control:CreateApiKeyCredentialProvider
├── bedrock-agentcore-control:GetCredentialProvider
├── bedrock-agentcore-control:ListCredentialProviders
├── bedrock-agentcore-control:UpdateCredentialProvider
└── bedrock-agentcore-control:DeleteCredentialProvider

IAM & Secrets:
├── iam:PassRole
├── secretsmanager:GetSecretValue
├── secretsmanager:CreateSecret
└── secretsmanager:UpdateSecret
```

**Configuration:**
```hcl
variable "credentials_role_name" {
  default = "test-agentcore-credentials-role-demo"
}
```

---

### 3. S3 Bucket (`gateway_specs_bucket`)
**Purpose:** Store OpenAPI specifications for gateway targets

**Features:**
- ✅ Auto-generated unique bucket name with account ID and region
- ✅ Versioning enabled for safe updates
- ✅ Public access blocked (security best practice)
- ✅ Fully tagged for resource management

**Configuration:**
```hcl
variable "s3_bucket_name" {
  default = "agentcore-gateway-specs"
}
```

**Bucket Name Format:**
```
{s3_bucket_name}-{account_id}-{region}
Example: agentcore-gateway-specs-123456789012-us-east-1
```

---

## 🚀 Deployment

### Step 1: Initialize Terraform
```bash
cd terraform
terraform init
```

### Step 2: Preview Changes
```bash
terraform plan
```

### Step 3: Deploy
```bash
terraform apply
```

### Custom Deployment (Optional)
```bash
terraform apply \
  -var="gateway_role_name=my-gateway-role" \
  -var="credentials_role_name=my-credentials-role" \
  -var="s3_bucket_name=my-bucket" \
  -var="aws_region=us-west-2" \
  -var="environment=prod"
```

---

## 📤 Outputs

After deployment, retrieve values using:

```bash
# Gateway Role
terraform output gateway_role_arn
terraform output gateway_role_name

# Credentials Role
terraform output credentials_role_arn
terraform output credentials_role_name

# S3 Bucket
terraform output s3_bucket_name
terraform output s3_bucket_arn

# Combined Environment Variables
terraform output env_file_content
```

---

## 🔧 Environment Configuration

### Option 1: Copy Terraform Output
```bash
terraform output env_file_content
```

This will output:
```
GATEWAY_ROLE_ARN=arn:aws:iam::ACCOUNT_ID:role/test-agentcore-lgateway-role-demo
CREDENTIALS_ROLE_ARN=arn:aws:iam::ACCOUNT_ID:role/test-agentcore-credentials-role-demo
S3_BUCKET_NAME=agentcore-gateway-specs-ACCOUNT_ID-us-east-1
```

### Option 2: Manual .env Update
Create/update `.env` file:
```bash
GATEWAY_ROLE_ARN=$(terraform output -raw gateway_role_arn)
CREDENTIALS_ROLE_ARN=$(terraform output -raw credentials_role_arn)
S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)
```

Or manually add to `.env`:
```env
GATEWAY_ROLE_ARN=arn:aws:iam::123456789012:role/test-agentcore-lgateway-role-demo
CREDENTIALS_ROLE_ARN=arn:aws:iam::123456789012:role/test-agentcore-credentials-role-demo
S3_BUCKET_NAME=agentcore-gateway-specs-123456789012-us-east-1
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Bedrock AgentCore Gateway Service                      │
│  (bedrock-agentcore.amazonaws.com)                      │
└──────┬──────────────────────────────┬────────────────────┘
       │ assumes                       │ assumes
       ▼                               ▼
┌─────────────────┐          ┌──────────────────────┐
│ Gateway Role    │          │ Credentials Role     │
├─────────────────┤          ├──────────────────────┤
│ - Create/manage │          │ - Create API Keys    │
│   gateways      │          │ - Manage Credentials │
│ - S3 access     │          │ - Secrets storage    │
│ - Auth services │          │ - Credential CRUD    │
└────────┬────────┘          └──────────────────────┘
         │                          │
         └────────────┬─────────────┘
                      ▼
            ┌──────────────────────┐
            │   S3 Bucket          │
            ├──────────────────────┤
            │ OpenAPI Specs        │
            │ Tool Definitions     │
            │ (Versioned & Secure) │
            └──────────────────────┘
```

---

## 🔐 Security Features

- ✅ **Least Privilege**: Each role has minimal required permissions
- ✅ **Service Trust**: Roles only trust the Bedrock AgentCore service
- ✅ **S3 Security**: Public access blocked, versioning enabled
- ✅ **Secrets Management**: Credentials stored in AWS Secrets Manager
- ✅ **IAM Tags**: All resources tagged for governance and tracking
- ✅ **Unique Bucket Names**: Account ID and region included to prevent conflicts

---

## 📁 Terraform Files

| File | Description |
|------|-------------|
| `terraform/main.tf` | Main resource definitions (roles, S3 bucket) |
| `terraform/variables.tf` | Variable definitions with defaults |
| `terraform.tfstate` | Terraform state file (do not commit) |
| `.gitignore` | Should exclude `*.tfstate` and `*.tfstate.backup` |

---

## 🧹 Cleanup

To destroy all resources:
```bash
terraform destroy
```

To destroy specific resources:
```bash
terraform destroy -target=aws_iam_role.gateway_role
terraform destroy -target=aws_iam_role.credentials_role
terraform destroy -target=aws_s3_bucket.gateway_specs_bucket
```

---

## 💡 Usage Examples

### Creating a Gateway with API Key Authentication
```bash
# 1. Create credential provider using Credentials Role
POST /credentials/create
{
  "providerName": "my-api-key-provider",
  "apiKey": "your-secret-key"
}

# Response includes credentialProviderArn

# 2. Create gateway target using Gateway Role
POST /gateways/{gatewayId}/targets
{
  "name": "my-tool",
  "openApiS3Uri": "s3://agentcore-gateway-specs-123456789012-us-east-1/specs/openapi.json",
  "credentialProviderArn": "arn:aws:bedrock:...:credential-provider/my-api-key-provider"
}
```

### Uploading OpenAPI Spec to S3
```bash
aws s3 cp openapi.json \
  s3://$(terraform output -raw s3_bucket_name)/specs/openapi.json

# Or using AWS SDK in your application
import boto3
s3 = boto3.client('s3')
s3.put_object(
  Bucket=os.getenv('S3_BUCKET_NAME'),
  Key='specs/my-api-openapi.json',
  Body=open('openapi.json').read()
)
```

---

## 🐛 Troubleshooting

### "Error: Invalid AWS Credentials"
- Ensure AWS credentials are configured: `aws configure`
- Check `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### "Error: S3 Bucket Already Exists"
- S3 bucket names are globally unique
- Customize with: `-var="s3_bucket_name=my-unique-name"`

### "Error: IAM Role Already Exists"
- Role names are unique per AWS account
- Customize with: `-var="gateway_role_name=my-custom-role"`

### Verify Deployment
```bash
# Check roles created
aws iam list-roles --query "Roles[?contains(RoleName, 'agentcore')]"

# Check S3 bucket
aws s3 ls | grep agentcore

# Verify role permissions
aws iam get-role-policy \
  --role-name test-agentcore-lgateway-role-demo \
  --policy-name test-agentcore-lgateway-role-demo-inline-policy
```

---

## ✅ Summary

You now have a complete Terraform infrastructure that:
- ✅ Creates Gateway Role for managing gateways
- ✅ Creates Credentials Role for managing API key providers
- ✅ Creates S3 Bucket for storing OpenAPI specifications
- ✅ Outputs all necessary values as environment variables
- ✅ Follows AWS security best practices
- ✅ Is fully reproducible and version-controlled

