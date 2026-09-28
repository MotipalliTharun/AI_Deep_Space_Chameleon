terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # TODO(sprint-0): wire up a remote backend (S3 + DynamoDB lock table) before
  # anyone applies this outside a local sandbox.
  # backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}
