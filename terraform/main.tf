terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
provider "aws" {
  region = var.aws_region
}
# Trust policy document matching Python: bedrock-agentcore.amazonaws.com
data "aws_iam_policy_document" "gateway_trust_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}
# Create the shared gateway role
resource "aws_iam_role" "gateway_role" {
  name               = var.gateway_role_name
  assume_role_policy = data.aws_iam_policy_document.gateway_trust_policy.json
  description        = "Role for Bedrock AgentCore Gateway"
  tags = {
    Name        = var.gateway_role_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
# Inline policy matching Python implementation exactly
resource "aws_iam_role_policy" "gateway_policy" {
  name   = "${var.gateway_role_name}-inline-policy"
  role   = aws_iam_role.gateway_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore-control:*",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "iam:PassRole",
          "cognito-idp:*",
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:GetWorkloadAccessToken",
          "bedrock-agentcore:InvokeCredentialProvider",
          "bedrock-agentcore:GetResourceApiKey"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
      }
    ]
  })
}
# Outputs for use in your application
output "gateway_role_arn" {
  description = "ARN of the shared gateway role"
  value       = aws_iam_role.gateway_role.arn
}
output "gateway_role_name" {
  description = "Name of the shared gateway role"
  value       = aws_iam_role.gateway_role.name
}
output "env_file_content" {
  description = "Content to add to your .env file"
  value       = "GATEWAY_ROLE_ARN=${aws_iam_role.gateway_role.arn}"
}
