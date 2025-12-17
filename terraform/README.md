# Terraform Setup for AgentCore Gateway Role

This Terraform configuration creates a shared IAM role that can be used for all AgentCore Gateways.

## Why Use a Shared Role?

Instead of creating a new IAM role every time a gateway is created (Python approach), we create the role once and reuse it for all gateways (TypeScript approach). Benefits:

- ✅ Fewer IAM operations
- ✅ Better resource management
- ✅ Easier to audit and maintain
- ✅ Single point of policy management
- ✅ Faster gateway creation

## Prerequisites

```bash
# Install Terraform
# https://www.terraform.io/downloads.html

# Configure AWS credentials
aws configure
```

## Usage

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Plan the deployment (Dev)

```bash
terraform plan -var-file="dev.tfvars"
```

### 3. Apply the configuration (Dev)

```bash
terraform apply -var-file="dev.tfvars"
```

Terraform will output:
```
Outputs:

env_file_content = "GATEWAY_ROLE_ARN=arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo"
gateway_role_arn = "arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo"
gateway_role_name = "sample-lambdagateway-role-demo"
```

### 4. Add to your .env file

Copy the `GATEWAY_ROLE_ARN` output and add to `ts-version/.env`:

```bash
# Option 1: Manual copy
echo "GATEWAY_ROLE_ARN=arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo" >> ../ts-version/.env

# Option 2: Terraform output directly
terraform output -raw env_file_content >> ../ts-version/.env
```

## File Structure

```
terraform/
├── main.tf              # Main configuration (IAM role)
├── variables.tf         # Variable definitions
├── outputs.tf           # Output values
├── dev.tfvars          # Development environment settings
├── prod.tfvars         # Production environment settings
└── README.md           # This file
```

## Configuration Files

### main.tf
- Creates the IAM role with correct trust policy
- Attaches basic execution policy
- Optional custom policy for gateway-specific permissions

### variables.tf
- `aws_region`: AWS region (default: us-east-1)
- `gateway_role_name`: Role name (default: sample-lambdagateway-role-demo)
- `environment`: Environment tag (dev, staging, prod)
- `create_custom_policy`: Whether to attach custom policy

### dev.tfvars & prod.tfvars
Environment-specific configurations:
- **Dev**: Uses basic policy only
- **Prod**: Includes custom policy with S3 permissions

## Common Commands

### View current state
```bash
terraform show
```

### Update to production
```bash
terraform plan -var-file="prod.tfvars"
terraform apply -var-file="prod.tfvars"
```

### Destroy resources (careful!)
```bash
# Dev
terraform destroy -var-file="dev.tfvars"

# Prod
terraform destroy -var-file="prod.tfvars"
```

### Get outputs
```bash
terraform output
terraform output gateway_role_arn
terraform output -raw env_file_content
```

## Integration with TypeScript Version

After creating the role with Terraform:

1. Get the role ARN from Terraform output
2. Add to `ts-version/.env`:
   ```env
   GATEWAY_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT:role/sample-lambdagateway-role-demo
   ```
3. Every gateway created will now use this shared role

## State Management

Terraform stores state in `terraform.tfstate` (local by default).

For production, use remote state:
```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "agentcore-gateway/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

## Permissions Required

Your AWS user needs these permissions:
- `iam:CreateRole`
- `iam:AttachRolePolicy`
- `iam:PutRolePolicy`
- `iam:GetRole`

## Troubleshooting

### "InvalidInput: Role name cannot contain special characters"
Check the `gateway_role_name` variable - ensure it only contains alphanumeric characters, hyphens, and underscores.

### "AccessDenied" errors
Ensure your AWS credentials have IAM permissions. Run:
```bash
aws iam get-user
```

### Need to update the role?
Edit `main.tf`, then:
```bash
terraform plan -var-file="dev.tfvars"
terraform apply -var-file="dev.tfvars"
```

## Next Steps

1. Run Terraform to create the role
2. Get the ARN from outputs
3. Add `GATEWAY_ROLE_ARN` to `.env`
4. Start the TypeScript server: `npm run dev`
5. All gateways will now use the shared role!

## References

- [AWS IAM Role Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role)
- [Terraform Variables](https://www.terraform.io/docs/language/values/variables.html)
- [Terraform Outputs](https://www.terraform.io/docs/language/values/outputs.html)

