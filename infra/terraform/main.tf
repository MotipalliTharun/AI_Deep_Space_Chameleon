# AI Space Chameleon — dev environment skeleton (PRD §7, §9 Sprint 0: "Terraform dev env")
#
# MVP hosting target: Docker on AWS, ECS Fargate, CloudFront CDN for the widget,
# Secrets Manager for keys (see docs/ARCHITECTURE.md). This file intentionally
# stays minimal for Sprint 0 — real modules (VPC, ECS services, RDS/pgvector,
# ElastiCache Redis, CloudFront) land as the API/workers are ready to deploy.

locals {
  name_prefix = "${var.project}-${var.environment}"
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# TODO(sprint-0/1): module "vpc" { ... }
# TODO(sprint-1): module "ecs_cluster" { ... }  (Fargate services: api, workers)
# TODO(sprint-1): module "database" { ... }     (RDS Postgres + pgvector extension)
# TODO(sprint-1): module "cache" { ... }        (ElastiCache Redis: queues, LRU cache, rate limits)
# TODO(sprint-1): module "widget_cdn" { ... }    (S3 + CloudFront, versioned by tenant per PRD §10)
# TODO(sprint-0): module "secrets" { ... }       (AWS Secrets Manager for LLM/API keys)
