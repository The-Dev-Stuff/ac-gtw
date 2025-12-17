# Manual AWS IAM Role Creation - Complete Guide (Matches Python Implementation)

This guide creates the **exact same role and policy** that the Python code creates, but done manually in the AWS Console.

## Overview

We'll create:
1. An IAM role that trusts the bedrock-agentcore service
2. An inline policy with comprehensive permissions for gateway management
3. This matches exactly what `create_agentcore_gateway_role()` does in Python

Takes about 10-15 minutes.

## Prerequisites

- AWS Account with admin access
- Link: https://console.aws.amazon.com/

---

## Step 1: Navigate to IAM Console

1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Search for "IAM" in the search bar
3. Click on **IAM** service
4. In the left sidebar, click **Roles**
5. Click the blue **Create role** button

---

## Step 2: Select Trusted Entity

On the "Select type of trusted entity" page:

1. Keep **AWS service** selected (default)
2. In the "Use cases" section, search for **"bedrock"**
3. Click on **Bedrock** if available
4. Click **Next**

**If Bedrock is not available:** That's okay. We'll manually fix the trust policy after creation.

---

## Step 3: Add Permissions (Initial)

On the "Add permissions" page:

**Option A - If you see a policy list:**
1. Search for any existing policy (optional - we'll add custom permissions anyway)
2. For now, you can skip selecting a policy

**Option B - Just click Next**
- We'll add the permissions via inline policy after role creation, which matches the Python code approach

Click **Next**

---

## Step 4: Name the Role

On the "Name, review, and create" page:

1. **Role name:** `sample-lambdagateway-role-demo`
2. **Description:** `Role for Bedrock AgentCore Gateway` (matches Python)
3. Review the settings
4. Click **Create role**

✅ Role created!

---

## Step 5: Fix Trust Policy (if needed)

If you didn't select Bedrock in Step 2:

1. Click on the role name to view its details
2. Go to the **"Trust relationships"** tab
3. Click **Edit trust policy**
4. Replace the JSON with:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

5. Click **Update policy**

---

## Step 6: Add the Inline Policy (IMPORTANT - This matches Python code)

This is the key step that matches the Python implementation!

1. You should be on the role details page
2. Click the **"Permissions"** tab
3. Look for **"Inline Policies"** section (or "Add permissions" button)
4. Click **"Add inline policy"** or **"Create inline policy"**
5. Choose **JSON** tab
6. Replace the default JSON with this policy (matches Python exactly):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore-control:*",
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "iam:PassRole",
                "cognito-idp:*",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:InvokeCredentialProvider",
                "bedrock-agentcore:GetResourceApiKey"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "*"
        }
    ]
}
```

7. Click **Review policy**
8. **Policy name:** `sample-lambdagateway-role-demo-inline-policy`
9. Click **Create policy**

✅ Inline policy added!

---

## Step 7: Verify the Role Configuration

Go back to the role details and verify:

**Trust Relationships tab:**
```json
{
    "Service": "bedrock-agentcore.amazonaws.com"
}
```
✓ Trusts bedrock-agentcore service

**Permissions tab - Inline Policies:**
```
sample-lambdagateway-role-demo-inline-policy
```
✓ Shows the policy with all permissions

---

## Step 8: Get the Role ARN

1. On the role details page, look for **ARN** (usually at the top)
2. It will look like:
```
arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo
```
3. **Copy this full ARN**

---

## Step 9: Add to Your .env File

**For TypeScript version:**
```
ts-version/.env
```

Add:
```env
GATEWAY_ROLE_ARN=arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo
```

Replace `123456789012` with your actual AWS Account ID.

---

## Step 10: Start Your Server

```bash
cd ts-version
npm run dev
```

Your API is running on `http://localhost:3000`

All gateways will now use this shared role with the exact permissions from the Python code! 🎉

---

## What Each Permission Does

The inline policy includes three statement blocks:

### Statement 1: Control Plane & Infrastructure
```json
{
    "Effect": "Allow",
    "Action": [
        "bedrock-agentcore-control:*",    // All gateway control operations
        "s3:GetObject",                   // Read OpenAPI specs from S3
        "s3:PutObject",                   // Write OpenAPI specs to S3
        "s3:ListBucket",                  // List S3 buckets
        "iam:PassRole",                   // Pass role to gateways
        "cognito-idp:*",                  // Cognito for authentication
        "sts:GetCallerIdentity"           // Get AWS account info
    ],
    "Resource": "*"
}
```

### Statement 2: Runtime Operations
```json
{
    "Effect": "Allow",
    "Action": [
        "bedrock-agentcore:GetWorkloadAccessToken",      // Get access tokens
        "bedrock-agentcore:InvokeCredentialProvider",    // Invoke credentials
        "bedrock-agentcore:GetResourceApiKey"            // Get API keys
    ],
    "Resource": "*"
}
```

### Statement 3: Secrets Management
```json
{
    "Effect": "Allow",
    "Action": [
        "secretsmanager:GetSecretValue"  // Retrieve secrets if needed
    ],
    "Resource": "*"
}
```

---

## Comparison: Python Code vs Manual Setup

| Aspect | Python Code | Manual Setup |
|--------|------------|--------------|
| **Trust Service** | `bedrock-agentcore.amazonaws.com` | Same ✓ |
| **Control Plane Perms** | `bedrock-agentcore-control:*` | Same ✓ |
| **Runtime Perms** | `bedrock-agentcore:*` operations | Same ✓ |
| **S3 Perms** | GetObject, PutObject, ListBucket | Same ✓ |
| **Other Perms** | IAM PassRole, Cognito, STS, Secrets | Same ✓ |
| **Inline Policy** | Yes, with name suffix | Yes ✓ |

**Result: 100% Match!** ✅

---

## Troubleshooting

### Q: I can't find the inline policy option
**A:** Try:
1. Click "Add permissions" button
2. Choose "Create inline policy"
3. Switch to JSON tab

### Q: "The policy document is too large"
**A:** This policy is within AWS limits. Try copying/pasting again, ensuring you have the entire JSON.

### Q: My gateway creation still fails
**A:** Make sure:
1. Trust policy has `bedrock-agentcore.amazonaws.com` (not `bedrock-agentcore-control`)
2. Inline policy is attached (not just a managed policy)
3. `GATEWAY_ROLE_ARN` in `.env` is correct
4. AWS credentials are configured locally

### Q: Do I need all these permissions?
**A:** For production, you can make it more restrictive. But for development/testing, this matches the Python implementation exactly.

---

## Files You'll Reference

| File | Purpose |
|------|---------|
| `gateway_service.py` (Python) | Shows what the role should be |
| `ts-version/.env` | Where you put the role ARN |
| `TERRAFORM_SETUP.md` | Alternative: use Terraform instead |

---

## Next Steps

1. ✅ Create role in AWS Console
2. ✅ Add inline policy matching Python code
3. ✅ Copy role ARN to `.env`
4. ✅ Start TypeScript server
5. ✅ Create gateways - they'll all use this role!

**You now have the exact same role as the Python code, but created manually!** 🚀

---

## For Future Reference

If you need to recreate this role:
- Role name: `sample-lambdagateway-role-demo`
- Trust: `bedrock-agentcore.amazonaws.com`
- Inline policy name: `sample-lambdagateway-role-demo-inline-policy`
- Copy the policy JSON from Step 6 above

