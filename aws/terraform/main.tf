locals {
  environment                 = var.environment
  environment_platform_domain = "${var.platform_subdomain}.${var.root_domain}"
  environment_api_domain      = "${var.api_subdomain}.${var.root_domain}"
  environment_namespace       = lower("${var.shared_resource_identifier}-platform-${local.environment}")
  ecr_repository_name         = local.environment_namespace
  ecr_repository_image        = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${local.ecr_repository_name}:latest"
  mysql_database              = substr("${var.shared_resource_identifier}_platform_${local.environment}", -64, -1)
  mysql_username              = local.mysql_database
  s3_bucket_name              = local.environment_platform_domain

  tags = merge(
    var.tags,
    {
      "smarter/environment"                 = local.environment
      "smarter/environment_platform_domain" = local.environment_platform_domain
      "smarter/environment_api_domain"      = local.environment_api_domain
      "smarter/environment_namespace"       = local.environment_namespace
    }
  )

}
