module "environment_storage" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.1"

  bucket                   = local.s3_bucket_name
  acl                      = "private"
  control_object_ownership = true
  object_ownership         = "ObjectWriter"
  tags                     = var.tags

  # attach_policy = true
  # policy        = data.aws_iam_policy_document.bucket_policy.json

  cors_rule = [
    {
      allowed_methods = ["GET", "POST", "PUT", "HEAD"]
      allowed_origins = [
        "https://${local.environment_domain}",
        "https://api.${local.environment_domain}",

        "http://${local.environment_domain}",
        "http://api.${local.environment_domain}",
      ]
      allowed_headers = ["*"]
      expose_headers = [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Method",
        "Access-Control-Allow-Header"
      ]
      max_age_seconds = 3000
    }
  ]
  versioning = {
    enabled = false
  }
}
