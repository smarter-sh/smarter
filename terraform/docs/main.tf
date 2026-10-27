#------------------------------------------------------------------------------
# docs.smarter.sh: the Sphinx site, built by make sphinx-docs, served by
# CloudFront from an S3 bucket, and uploaded by make sphinx-publish.
#
# CloudFront reads the bucket through an origin access control (OAC), and the
# bucket policy allows only this distribution.
#
# These resources were made by hand in the AWS console before this stack
# existed. The import blocks in imports.tf adopt them into the state; the
# configuration here describes them as they are, so adopting them changes
# nothing.
#------------------------------------------------------------------------------

data "aws_route53_zone" "this" {
  name         = var.hosted_zone_name
  private_zone = false
}

#------------------------------------------------------------------------------
# TLS certificate, validated by DNS
#------------------------------------------------------------------------------
resource "aws_acm_certificate" "docs" {
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate_validation" {
  for_each = {
    for option in aws_acm_certificate.docs.domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      type   = option.resource_record_type
      record = option.resource_record_value
    }
  }

  zone_id         = data.aws_route53_zone.this.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 300
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "docs" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.docs.arn
  validation_record_fqdns = [for record in aws_route53_record.certificate_validation : record.fqdn]
}

#------------------------------------------------------------------------------
# The bucket that holds the built site
#------------------------------------------------------------------------------
resource "aws_s3_bucket" "docs" {
  bucket = local.bucket_name
}

# ACLs stay enabled, as the bucket was made. make sphinx-publish used to upload
# with --acl public-read, and older objects still carry that ACL. CloudFront
# ignores ACLs: it reads through the OAC, so uploads no longer set one.
resource "aws_s3_bucket_ownership_controls" "docs" {
  bucket = aws_s3_bucket.docs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket = aws_s3_bucket.docs.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

#------------------------------------------------------------------------------
# CloudFront
#------------------------------------------------------------------------------
resource "aws_cloudfront_origin_access_control" "docs" {
  name                              = "oac-docs.smarter.sh.s3.us-east-2.amazonaws.com-mq41pqv3e4x"
  description                       = "Created by CloudFront"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# The site used to be served under /en/latest/. Old links are redirected to
# the same page at the root.
resource "aws_cloudfront_function" "redirect" {
  provider = aws.us_east_1
  name     = "docs-smarter-sh-redirect"
  runtime  = "cloudfront-js-2.0"
  publish  = true
  code     = file("${path.module}/redirect.js")
}

# AWS's managed policy for static content: long TTLs, compressed, no cookies
# or query strings in the cache key.
data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

resource "aws_cloudfront_distribution" "docs" {
  comment             = var.domain_name
  aliases             = [var.domain_name]
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = "http2"
  price_class         = "PriceClass_All"
  default_root_object = "index.html"

  tags = {
    Name = var.domain_name
  }

  origin {
    origin_id                = "docs.smarter.sh.s3.us-east-2.amazonaws.com-mq41p9ca84o"
    domain_name              = aws_s3_bucket.docs.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.docs.id
  }

  default_cache_behavior {
    target_origin_id       = "docs.smarter.sh.s3.us-east-2.amazonaws.com-mq41p9ca84o"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = data.aws_cloudfront_cache_policy.caching_optimized.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.redirect.arn
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.docs.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

resource "aws_s3_bucket_policy" "docs" {
  bucket = aws_s3_bucket.docs.id
  policy = jsonencode({
    Version = "2008-10-17"
    Id      = "PolicyForCloudFrontPrivateContent"
    Statement = [{
      Sid       = "AllowCloudFrontServicePrincipal"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.docs.arn}/*"
      Condition = { ArnLike = { "AWS:SourceArn" = aws_cloudfront_distribution.docs.arn } }
    }]
  })
}

#------------------------------------------------------------------------------
# DNS: docs.smarter.sh -> CloudFront
#------------------------------------------------------------------------------
resource "aws_route53_record" "docs" {
  zone_id = data.aws_route53_zone.this.zone_id
  name    = var.domain_name
  type    = "CNAME"
  ttl     = 300
  records = [aws_cloudfront_distribution.docs.domain_name]
}
