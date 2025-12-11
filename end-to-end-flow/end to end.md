![img.png](img.png)

## Permissions needed (For scenario where api key was used)

**Role:** `sample-lambdagateway-role-demo`  
**Policy:** `sample-lambdagateway-role-demo-inline-policy`

| Action | Purpose |
|--------|---------|
| `bedrock-agentcore-control:*` | Manage gateways and targets |
| `bedrock-agentcore:GetWorkloadAccessToken` | Get workload identity token |
| `bedrock-agentcore:InvokeCredentialProvider` | Invoke the credential provider |
| `bedrock-agentcore:GetResourceApiKey` | Retrieve API key from Token Vault |
| `secretsmanager:GetSecretValue` | Read secrets from Secrets Manager |
| `s3:GetObject` | Read OpenAPI specs from S3 |
| `s3:PutObject` | Upload OpenAPI specs to S3 |
| `s3:ListBucket` | List S3 bucket contents |
| `iam:PassRole` | Pass IAM role to services |
| `cognito-idp:*` | Cognito user pool operations |
| `sts:GetCallerIdentity` | Get AWS caller identity |

**Resource:** `*` (should be scoped down for production)
