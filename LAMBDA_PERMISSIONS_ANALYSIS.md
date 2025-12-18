# Lambda Permissions Analysis

## Your Current User Permissions

Your AWS user **Administrator** (ARN: `arn:aws:iam::606279327502:user/Administrator`) has the following inline policy: **bedrock-agentcore-gateway-policy**

### Current Permissions Breakdown

#### 1. Bedrock AgentCore Gateway Operations
```
bedrock-agentcore:GetGateway
bedrock-agentcore:ListGateways
bedrock-agentcore:CreateGateway
bedrock-agentcore:UpdateGateway
bedrock-agentcore:DeleteGateway
bedrock-agentcore:GetGatewayTarget
bedrock-agentcore:ListGatewayTargets
bedrock-agentcore:CreateGatewayTarget
bedrock-agentcore:UpdateGatewayTarget
bedrock-agentcore:DeleteGatewayTarget
```

#### 2. API Key Credential Provider Operations
```
bedrock-agentcore:CreateApiKeyCredentialProvider
bedrock-agentcore:GetApiKeyCredentialProvider
bedrock-agentcore:ListApiKeyCredentialProviders
```

#### 3. S3 Operations
```
s3:GetObject
s3:PutObject
s3:ListBucket
```

#### 4. IAM Operations
```
iam:PassRole
iam:CreateRole
iam:GetRole
iam:PutRolePolicy
```

---

## Required Permissions for Lambda Deployment

If you deploy the gateway-poc server as a Lambda function, it will need the following permissions:

### Minimal Required Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAgentCoreGatewayOperations",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetGateway",
        "bedrock-agentcore:ListGateways",
        "bedrock-agentcore:CreateGateway",
        "bedrock-agentcore:UpdateGateway",
        "bedrock-agentcore:DeleteGateway",
        "bedrock-agentcore:GetGatewayTarget",
        "bedrock-agentcore:ListGatewayTargets",
        "bedrock-agentcore:CreateGatewayTarget",
        "bedrock-agentcore:UpdateGatewayTarget",
        "bedrock-agentcore:DeleteGatewayTarget"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CredentialProviderOperations",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateApiKeyCredentialProvider",
        "bedrock-agentcore:GetApiKeyCredentialProvider",
        "bedrock-agentcore:ListApiKeyCredentialProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Operations",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRole",
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

### Additional Considerations for Lambda

#### 1. **Lambda Execution Role Trust Policy**
The Lambda execution role needs to trust the Lambda service:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

#### 2. **CloudWatch Logs (Essential for Debugging)**
```json
{
  "Sid": "CloudWatchLogs",
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:*:*:*"
}
```

#### 3. **Additional Permissions (If Needed)**
- **VPC Access** (if Lambda needs to access private resources):
  ```json
  {
    "Sid": "VPCAccess",
    "Effect": "Allow",
    "Action": [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface"
    ],
    "Resource": "*"
  }
  ```

- **Secrets Manager** (for storing API keys):
  ```json
  {
    "Sid": "SecretsManager",
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue",
      "secretsmanager:CreateSecret",
      "secretsmanager:UpdateSecret"
    ],
    "Resource": "*"
  }
  ```

---

## Comparison: User vs Lambda Permissions

| Permission | Your User | Lambda Needs |
|-----------|-----------|--------------|
| Bedrock AgentCore Operations | ✅ Yes | ✅ Yes |
| Credential Provider Operations | ✅ Yes | ✅ Yes |
| S3 Operations | ✅ Yes | ✅ Yes |
| IAM PassRole | ✅ Yes | ⚠️ Only if creating roles |
| IAM CreateRole/GetRole/PutRolePolicy | ✅ Yes | ❌ No (handled by Terraform) |
| CloudWatch Logs | ❌ No | ✅ Yes (essential for Lambda) |

---

## Recommended Lambda Execution Role Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAgentCoreOperations",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetGateway",
        "bedrock-agentcore:ListGateways",
        "bedrock-agentcore:CreateGateway",
        "bedrock-agentcore:UpdateGateway",
        "bedrock-agentcore:DeleteGateway",
        "bedrock-agentcore:GetGatewayTarget",
        "bedrock-agentcore:ListGatewayTargets",
        "bedrock-agentcore:CreateGatewayTarget",
        "bedrock-agentcore:UpdateGatewayTarget",
        "bedrock-agentcore:DeleteGatewayTarget",
        "bedrock-agentcore:CreateApiKeyCredentialProvider",
        "bedrock-agentcore:GetApiKeyCredentialProvider",
        "bedrock-agentcore:ListApiKeyCredentialProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Operations",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRole",
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

---

## Summary

Your user has a well-scoped policy for managing Bedrock AgentCore gateways and credentials. When deploying as Lambda:

1. ✅ Keep all the Bedrock AgentCore permissions
2. ✅ Keep S3 and IAM PassRole permissions
3. ✅ Add CloudWatch Logs permissions (essential for debugging)
4. ⚠️ Remove role creation permissions (let Terraform handle that)
5. ⚠️ Consider adding Secrets Manager if storing credentials

The key difference is that Lambda needs CloudWatch Logs access for monitoring and debugging, which your user policy doesn't explicitly require since you're running from your local machine.

