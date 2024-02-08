#------------------------------------------------------------------------------
# SSL/TLS certs issued in the AWS region for ALB
#------------------------------------------------------------------------------
provider "aws" {
  alias  = "environment_region"
  region = var.aws_region
}

provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
}

#------------------------------------------------------------------------------
# SSL/TLS certs issued in us-east-1 for Cloudfront
#------------------------------------------------------------------------------

module "acm_environment_domain" {
  source  = "terraform-aws-modules/acm/aws"
  version = "~> 5.0"

  providers = {
    aws = aws.us-east-1
  }

  domain_name       = local.environment_domain
  zone_id           = aws_route53_zone.environment_domain.id
  validation_method = "DNS"

  subject_alternative_names = [
    "*.${local.environment_domain}",
  ]

  wait_for_validation = true

  # adding the Usage tag as a way to differentiate this cert from the one created by
  # the eks clb ingress, of which we have no control.
  tags = var.tags

}
