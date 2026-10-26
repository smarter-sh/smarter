#------------------------------------------------------------------------------
# Adopts docs.smarter.sh's hand-made resources into the state. Each id is
# looked up rather than written here, so that no account id is in this public
# repository. Once applied, these blocks do nothing, and can be deleted.
#------------------------------------------------------------------------------

data "aws_acm_certificate" "docs" {
  provider    = aws.us_east_1
  domain      = var.domain_name
  most_recent = true
}

data "aws_cloudfront_distribution" "docs" {
  id = "E3J3PFZATCQOFX"
}

import {
  to = aws_acm_certificate.docs
  id = data.aws_acm_certificate.docs.arn
}

import {
  to = aws_route53_record.certificate_validation["docs.smarter.sh"]
  id = "${data.aws_route53_zone.this.zone_id}_${trimsuffix(one(aws_acm_certificate.docs.domain_validation_options).resource_record_name, ".")}_CNAME"
}

import {
  to = aws_s3_bucket.docs
  id = "docs.smarter.sh"
}

import {
  to = aws_s3_bucket_ownership_controls.docs
  id = "docs.smarter.sh"
}

import {
  to = aws_s3_bucket_public_access_block.docs
  id = "docs.smarter.sh"
}

import {
  to = aws_s3_bucket_server_side_encryption_configuration.docs
  id = "docs.smarter.sh"
}

import {
  to = aws_s3_bucket_policy.docs
  id = "docs.smarter.sh"
}

import {
  to = aws_cloudfront_origin_access_control.docs
  id = "E11LNHRU61RWG0"
}

import {
  to = aws_cloudfront_function.redirect
  id = "docs-smarter-sh-redirect"
}

import {
  to = aws_cloudfront_distribution.docs
  id = data.aws_cloudfront_distribution.docs.id
}

import {
  to = aws_route53_record.docs
  id = "${data.aws_route53_zone.this.zone_id}_docs.smarter.sh_CNAME"
}
