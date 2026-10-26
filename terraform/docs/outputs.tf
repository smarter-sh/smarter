#------------------------------------------------------------------------------
# Outputs, which make sphinx-publish can read: terraform -chdir=terraform/docs output -raw <name>.
#------------------------------------------------------------------------------

output "url" {
  description = "The documentation site."
  value       = "https://${var.domain_name}/"
}

output "bucket_name" {
  description = "The S3 bucket that make sphinx-publish uploads the built site to."
  value       = aws_s3_bucket.docs.id
}

output "distribution_id" {
  description = "The CloudFront distribution that make sphinx-publish invalidates."
  value       = aws_cloudfront_distribution.docs.id
}
