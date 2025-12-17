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
# Trust policy document for credentials provider role
# Allows the application/service to assume this role
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
# Create the credentials provider role
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
# Policy for credentials provider role
resource "aws_iam_role_policy" "credentials_policy" {
  name   = "${var.credentials_role_name}-inline-policy"
  role   = aws_iam_role.credentials_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore-control:CreateApiKeyCredentialProvider",
          "bedrock-agentcore-control:GetCredentialProvider",
          "bedrock-agentcore-control:ListCredentialProviders",
          "bedrock-agentcore-control:UpdateCredentialProvider",
          "bedrock-agentcore-control:DeleteCredentialProvider"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:CreateSecret",
          "secretsmanager:UpdateSecret"
        ]
        Resource = "*"
      }
    ]
  })
}

# Create S3 bucket for storing OpenAPI specs
resource "aws_s3_bucket" "gateway_specs_bucket" {
  bucket = "${var.s3_bucket_name}-${data.aws_caller_identity.current.account_id}-${var.aws_region}"

  tags = {
    Name        = var.s3_bucket_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Enable versioning on the bucket
resource "aws_s3_bucket_versioning" "gateway_specs_versioning" {
  bucket = aws_s3_bucket.gateway_specs_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access to the bucket
resource "aws_s3_bucket_public_access_block" "gateway_specs_pab" {
  bucket = aws_s3_bucket.gateway_specs_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}

# Outputs for use in your application
output "gateway_role_arn" {
  description = "ARN of the shared gateway role"
  value       = aws_iam_role.gateway_role.arn
}
output "gateway_role_name" {
  description = "Name of the shared gateway role"
  value       = aws_iam_role.gateway_role.name
}
output "credentials_role_arn" {
  description = "ARN of the credentials provider role"
  value       = aws_iam_role.credentials_role.arn
}
output "credentials_role_name" {
  description = "Name of the credentials provider role"
  value       = aws_iam_role.credentials_role.name
}
output "s3_bucket_name" {
  description = "Name of the S3 bucket for storing OpenAPI specs"
  value       = aws_s3_bucket.gateway_specs_bucket.id
}
output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.gateway_specs_bucket.arn
}
output "env_file_content" {
  description = "Content to add to your .env file"
  value       = "GATEWAY_ROLE_ARN=${aws_iam_role.gateway_role.arn}\nCREDENTIALS_ROLE_ARN=${aws_iam_role.credentials_role.arn}\nS3_BUCKET_NAME=${aws_s3_bucket.gateway_specs_bucket.id}"
}
