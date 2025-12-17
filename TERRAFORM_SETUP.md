# Quick Terraform Setup Guide

## TL;DR

Create a shared IAM role once, use it for all gateways.

```bash
# 1. Go to terraform directory
cd terraform

# 2. Initialize Terraform
terraform init

# 3. Apply for development
terraform apply -var-file="dev.tfvars"

# 4. Copy the role ARN to your .env
echo "GATEWAY_ROLE_ARN=$(terraform output -raw gateway_role_arn)" >> ../ts-version/.env

# 5. Start the TypeScript server
cd ../ts-version
npm run dev
```

## What This Does

Creates an AWS IAM role that:
- ✅ Trusts bedrock-agentcore-control service
- ✅ Has lambda execution permissions
- ✅ Can be used by all your gateways
- ✅ Is created once and reused

## Before & After

### Python Approach (Creates role each time)
```
Create Gateway #1 → Create Role #1
Create Gateway #2 → Create Role #2
Create Gateway #3 → Create Role #3
```

### TypeScript Approach (Reuse same role)
```
Terraform: Create Role (once) → sample-lambdagateway-role-demo
Create Gateway #1 → Use Role
Create Gateway #2 → Use Role
Create Gateway #3 → Use Role
```

## Step-by-Step

### 1. Prerequisites
```bash
# Check you have AWS CLI configured
aws sts get-caller-identity

# Check you have Terraform installed
terraform --version
```

### 2. Initialize
```bash
cd terraform
terraform init
```

You should see:
```
Terraform has been successfully initialized!
```

### 3. Plan (optional - see what will be created)
```bash
terraform plan -var-file="dev.tfvars"
```

### 4. Apply (create the role)
```bash
terraform apply -var-file="dev.tfvars"
```

Type `yes` when prompted.

You'll see output:
```
Outputs:

env_file_content = "GATEWAY_ROLE_ARN=arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo"
gateway_role_arn = "arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo"
gateway_role_name = "sample-lambdagateway-role-demo"
```

### 5. Update Your .env
```bash
# Option A: Manual - Copy the GATEWAY_ROLE_ARN value
# Edit ts-version/.env and add:
GATEWAY_ROLE_ARN=arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo

# Option B: Automatic
terraform output -raw env_file_content >> ../ts-version/.env

# Verify it was added
cat ../ts-version/.env | grep GATEWAY_ROLE_ARN
```

### 6. Test
```bash
cd ../ts-version
npm run dev

# In another terminal
curl http://localhost:3000/health
```

## For Production

When ready for production:

```bash
# Plan
terraform plan -var-file="prod.tfvars"

# Apply
terraform apply -var-file="prod.tfvars"

# Get the production role ARN
terraform output -raw gateway_role_arn
```

Then update your production `.env` with the production role ARN.

## Common Errors & Fixes

### "UnauthorizedOperation"
Your AWS user doesn't have IAM permissions.
```bash
# Check your permissions
aws iam get-user
```

### "EntityAlreadyExists: Role with name sample-lambdagateway-role-demo already exists"
The role was already created. Either:
- Delete it first: `aws iam delete-role --role-name sample-lambdagateway-role-demo`
- Or use a different name in `dev.tfvars`

### "InvalidInput: Role name cannot contain special characters"
Role names can only contain: `[a-zA-Z0-9+=,.@_-]`
Update the `gateway_role_name` in your `.tfvars` file.

## Cleaning Up

If you want to delete everything:
```bash
cd terraform
terraform destroy -var-file="dev.tfvars"
```

Type `yes` to confirm.

## File Reference

| File | Purpose |
|------|---------|
| main.tf | The actual IAM role definition |
| variables.tf | Input variables |
| outputs.tf | Output values (role ARN, etc.) |
| dev.tfvars | Development environment settings |
| prod.tfvars | Production environment settings |
| README.md | Detailed documentation |

## Architecture

```
Terraform Plan
    ↓
Create IAM Role (bedrock-agentcore-control trust)
    ↓
Attach Lambda Execution Policy
    ↓
Output Role ARN
    ↓
Add to .env as GATEWAY_ROLE_ARN
    ↓
TypeScript Server
    ↓
All Gateways Use Shared Role ✓
```

## Next

After running Terraform:
1. Your role is created and ready
2. All new gateways will use this role automatically
3. No more role creation on each gateway
4. Much cleaner and more efficient!

---

**That's it! One-time setup, then reuse forever.** 🚀

