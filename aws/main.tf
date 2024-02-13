locals {
  environment           = var.environment
  environment_domain    = local.environment == "prod" ? "api.${var.root_domain}" : "${var.subdomain}.api.${var.root_domain}"
  environment_namespace = lower("${var.shared_resource_identifier}-api-${local.environment}")
  ecr_repository_name   = local.environment_namespace
  ecr_repository_image  = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${local.ecr_repository_name}:latest"
  mysql_database        = substr("${var.shared_resource_identifier}_api_${local.environment}", -64, -1)
  mysql_username        = local.mysql_database
  s3_bucket_name        = local.environment_domain
}
