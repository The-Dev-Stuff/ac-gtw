# Shared Gateway Role Setup - Complete Answer

## Your Question
> "Currently in the python project, we create a new gateway role or policy each time a gateway is created. In the ts-version, I don't want to do this, I want to use the same role/policy to create every gateway. Is this possible? How would i do it via terraform?"

## Answer: YES, 100% Possible ✅

### What We Already Did in TypeScript Version

The TypeScript code is **already configured** to use a pre-existing role:

```typescript
// From ts-version/.env
GATEWAY_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT_ID:role/sample-lambdagateway-role-demo

// From ts-version/src/api/app.controller.ts
const gatewayInfo = await this.gatewayService.createGateway(
  request.gateway_name,
  GATEWAY_ROLE_ARN,  // ← Reuses the same role every time
  true,
  authConfig,
  request.description,
);
```

No role creation logic - just reuses the same one!

### Terraform Solution (Infrastructure as Code)

I've created a complete Terraform setup in `/terraform` directory:

#### Files Created:

1. **`main.tf`** - Creates the IAM role
   - Sets up trust policy for bedrock-agentcore-control
   - Attaches execution policies
   - Optional custom policies

2. **`variables.tf`** - Configuration options
   - AWS region
   - Role name
   - Environment tags
   - Custom policy toggle

3. **`outputs.tf`** - Output values
   - Role ARN (for your .env)
   - Role name
   - Pre-formatted env content

4. **`dev.tfvars`** - Development configuration
   - Uses basic policy only
   - Role name: `sample-lambdagateway-role-demo`

5. **`prod.tfvars`** - Production configuration
   - Includes custom policy
   - Role name: `sample-lambdagateway-role-prod`
   - More restrictive permissions

6. **`README.md`** - Complete Terraform documentation

### How It Works

#### Before (Python - Creates role each time)
```
Gateway 1 created → IAM role 1 created
Gateway 2 created → IAM role 2 created
Gateway 3 created → IAM role 3 created
Result: 3 roles, hard to manage
```

#### After (TypeScript - Reuses same role)
```
Terraform applied → IAM role created (once)
Gateway 1 created → Uses shared role
Gateway 2 created → Uses shared role
Gateway 3 created → Uses shared role
Result: 1 role, easy to manage
```

### Quick Setup

```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Create the role
terraform apply -var-file="dev.tfvars"

# 3. Get the role ARN
terraform output gateway_role_arn
# Output: arn:aws:iam::123456789012:role/sample-lambdagateway-role-demo

# 4. Add to your .env
echo "GATEWAY_ROLE_ARN=$(terraform output -raw gateway_role_arn)" >> ../ts-version/.env

# 5. Start server
cd ../ts-version
npm run dev
```

All gateways now use the shared role! ✅

### Why This Approach is Better

| Aspect | Python (New role each time) | TypeScript (Shared role) |
|--------|----------------------------|------------------------|
| **IAM Operations** | 3 create role calls for 3 gateways | 1 create role call (Terraform) |
| **Management** | Hard - which role for which gateway? | Easy - all gateways use same role |
| **Permissions** | Hard to audit - scattered policies | Easy - centralized policy |
| **Cost** | More IAM API calls | Fewer API calls |
| **Scalability** | Doesn't scale well | Scales perfectly |
| **Infrastructure** | Ad-hoc | Code-managed (IaC) |

### Terraform Architecture Diagram

```
┌─────────────────────────────────────┐
│     Terraform Configuration         │
│  ┌──────────────────────────────┐   │
│  │ main.tf                      │   │
│  │ Creates IAM role with trust  │   │
│  │ policy for bedrockagentcore  │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │ variables.tf                 │   │
│  │ Configuration: region, name, │   │
│  │ environment, policy flag     │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │ *.tfvars                     │   │
│  │ Environment-specific values  │   │
│  │ (dev.tfvars, prod.tfvars)    │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
         ↓
    terraform apply
         ↓
┌─────────────────────────────────────┐
│    AWS IAM Role Created             │
│ ┌──────────────────────────────┐    │
│ │ Role Name                    │    │
│ │ sample-lambdagateway-...     │    │
│ ├──────────────────────────────┤    │
│ │ Trust Policy                 │    │
│ │ bedrock-agentcore service    │    │
│ ├──────────────────────────────┤    │
│ │ Attached Policies            │    │
│ │ - Lambda Basic Execution     │    │
│ │ - (optional) Custom Policy   │    │
│ └──────────────────────────────┘    │
└─────────────────────────────────────┘
         ↓
   Get Role ARN
         ↓
   Add to .env
         ↓
┌─────────────────────────────────────┐
│     TypeScript Server Starts        │
│   GATEWAY_ROLE_ARN=arn:aws...       │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Create Gateway 1 → Use shared role│
│   Create Gateway 2 → Use shared role│
│   Create Gateway 3 → Use shared role│
│          ✅ All done!               │
└─────────────────────────────────────┘
```

### File Locations

```
gateway-poc/
├── terraform/                          ← NEW
│   ├── main.tf                        ← Terraform config
│   ├── variables.tf                   ← Variable definitions
│   ├── outputs.tf                     ← Output values
│   ├── dev.tfvars                     ← Dev environment
│   ├── prod.tfvars                    ← Prod environment
│   ├── README.md                      ← Terraform docs
│   └── .gitignore                     ← Git config for Terraform
├── ts-version/
│   ├── .env                           ← Update with GATEWAY_ROLE_ARN
│   └── ...
├── TERRAFORM_SETUP.md                 ← Quick setup guide (NEW)
└── ...
```

### Summary

**Yes, it's possible and we've set it up for you!**

1. ✅ TypeScript code already configured for shared role
2. ✅ Terraform templates created for easy deployment
3. ✅ Dev and Prod configurations provided
4. ✅ Complete documentation included
5. ✅ One-time setup, reuse forever

**Next Steps:**
1. Read `TERRAFORM_SETUP.md` for quick start
2. Read `terraform/README.md` for detailed docs
3. Run `terraform apply -var-file="dev.tfvars"`
4. Add role ARN to your `.env`
5. Start the server and you're done!

**All your gateways will now share the same role!** 🚀

