# Credentials Provider Role Setup

## Overview
Added IAM role creation for managing Bedrock AgentCore credential providers. This role is used by the credentials service to create and manage API key credential providers for gateway targets/tools.

## Changes Made

### 1. Terraform Variables (`terraform/variables.tf`)
Added new variable for credentials role name:
```hcl
variable "credentials_role_name" {
  description = "Name of the credentials/credential provider role"
  type        = string
  default     = "test-agentcore-credentials-role-demo"
}
```

### 2. Terraform Configuration (`terraform/main.tf`)
Added the following resources:

#### a. Trust Policy for Credentials Role
```hcl
data "aws_iam_policy_document" "credentials_trust_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}
```

#### b. Credentials Role
```hcl
resource "aws_iam_role" "credentials_role" {
  name               = var.credentials_role_name
  assume_role_policy = data.aws_iam_policy_document.credentials_trust_policy.json
  description        = "Role for Bedrock AgentCore Credential Provider Management"
  tags = {
    Name        = var.credentials_role_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

#### c. Credentials Role Policy
The role includes permissions for:
- **Credential Provider Operations**:
  - `bedrock-agentcore-control:CreateApiKeyCredentialProvider` - Create API key credentials
  - `bedrock-agentcore-control:GetCredentialProvider` - Retrieve credentials
  - `bedrock-agentcore-control:ListCredentialProviders` - List all credentials
  - `bedrock-agentcore-control:UpdateCredentialProvider` - Update credentials
  - `bedrock-agentcore-control:DeleteCredentialProvider` - Delete credentials

- **IAM Operations**:
  - `iam:PassRole` - Allow passing roles to services

- **Secrets Manager Operations**:
  - `secretsmanager:GetSecretValue` - Retrieve secrets
  - `secretsmanager:CreateSecret` - Create secrets
  - `secretsmanager:UpdateSecret` - Update secrets

#### d. Updated Outputs
Added outputs for the credentials role:
```hcl
output "credentials_role_arn" {
  description = "ARN of the credentials provider role"
  value       = aws_iam_role.credentials_role.arn
}

output "credentials_role_name" {
  description = "Name of the credentials provider role"
  value       = aws_iam_role.credentials_role.name
}
```

Updated env_file_content output to include both roles:
```hcl
output "env_file_content" {
  value = "GATEWAY_ROLE_ARN=${aws_iam_role.gateway_role.arn}\nCREDENTIALS_ROLE_ARN=${aws_iam_role.credentials_role.arn}"
}
```

## Code Context

The credentials role is used by the `CredentialsService` in `ts-version/src/services/credentials/credentials.service.ts`:

```typescript
async createOrGetApiKeyCredentialProvider(
  providerName: string,
  apiKey: string,
): Promise<string> {
  const client = new BedrockAgentCoreControlClient({
    region: this.awsRegion,
  });
  
  const command = new CreateApiKeyCredentialProviderCommand({
    name: providerName,
    apiKey: apiKey,
  });
  
  const response = await client.send(command);
  return response.credentialProviderArn || '';
}
```

This service is called from the `AppController` when creating tools/targets:

```typescript
private async registerToolWithGateway(
  gatewayId: string,
  targetName: string,
  openApiS3Uri: string,
  auth: any,
  description?: string,
) {
  // ... credential setup code ...
  const credentialProviderArn =
    await this.credentialsService.createOrGetApiKeyCredentialProvider(
      apiKeyProviderName,
      apiKey,
    );
  
  const response = await this.toolsService.createGatewayTarget(
    gatewayId,
    targetName,
    openApiS3Uri,
    credentialProviderArn,
    apiKeyParamName,
    apiKeyLocation,
    description,
  );
}
```

## Usage

When running Terraform, you can customize the credentials role name:

```bash
# Using default values
terraform apply

# Or with custom role names
terraform apply -var="credentials_role_name=my-custom-credentials-role"
```

After deployment, retrieve the role ARN from Terraform outputs:
```bash
terraform output credentials_role_arn
```

Update your `.env` file with:
```
CREDENTIALS_ROLE_ARN=<arn-from-terraform>
```

## Summary

✅ **Created Credentials Provider Role** - Manages API key credential providers for gateway targets
✅ **Proper Permissions** - Credentials role has limited, focused permissions for credential operations
✅ **Trust Relationship** - Role trusts the Bedrock AgentCore service
✅ **Terraform Outputs** - Role ARN available as Terraform output for environment configuration

