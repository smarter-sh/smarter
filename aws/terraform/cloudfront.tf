
# create an environment-specific cloudfront distribution

locals {
  s3_bucket_domain = "${local.s3_bucket_name}.s3.${var.aws_region}.amazonaws.com"
  cdn_name         = "cdn.${local.environment_domain}"
}

# see ./route53.tf for creation of data.aws_route53_zone.environment_domain.id
resource "aws_route53_record" "cdn_environment_domain" {
  zone_id = aws_route53_zone.environment_domain.id
  name    = local.cdn_name
  type    = "A"

  alias {
    name                   = module.cdn_environment_domain.cloudfront_distribution_domain_name
    zone_id                = module.cdn_environment_domain.cloudfront_distribution_hosted_zone_id
    evaluate_target_health = false
  }

}


module "cdn_environment_domain" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "~> 3.2"

  aliases = [local.cdn_name]

  comment             = "Smarter CDN"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = "PriceClass_All"
  retain_on_delete    = false
  wait_for_deployment = false

  origin = {
    s3_bucket = {
      domain_name = "${local.s3_bucket_domain}"
    }
  }

  default_cache_behavior = {
    target_origin_id       = "s3_bucket"
    viewer_protocol_policy = "allow-all"

    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods  = ["GET", "HEAD"]
    compress        = true
    query_string    = true
  }

  ordered_cache_behavior = [
    {
      path_pattern           = "/static/*"
      target_origin_id       = "s3_bucket"
      viewer_protocol_policy = "redirect-to-https"

      allowed_methods = ["GET", "HEAD", "OPTIONS"]
      cached_methods  = ["GET", "HEAD"]
      compress        = true
      query_string    = true
    }
  ]

  viewer_certificate = {
    acm_certificate_arn = module.acm_environment_domain.acm_certificate_arn
    ssl_support_method  = "sni-only"
  }

  tags = local.tags
}
