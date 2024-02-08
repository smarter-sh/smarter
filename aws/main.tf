locals {
  environment           = "dev"
  environment_domain    = "${var.subdomain}.api.${var.root_domain}"
  environment_namespace = lower(replace("${var.root_domain}.api.${var.subdomain}", ".", "-"))
  s3_bucket_name        = local.environment_domain
  ecr_repository_name   = var.shared_resource_identifier
  ecr_repository_image  = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${local.ecr_repository_name}:latest"
  mysql_database        = "${var.shared_resource_identifier}_${local.environment}"
}
