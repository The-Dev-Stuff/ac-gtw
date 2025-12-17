variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
variable "gateway_role_name" {
  description = "Name of the shared gateway role"
  type        = string
  default     = "test-agentcore-lgateway-role-demo"
}
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}
