variable "aws_region" {
  description = "AWS region for the dev environment."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev | staging | production)."
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Project tag applied to all resources."
  type        = string
  default     = "space-chameleon"
}
