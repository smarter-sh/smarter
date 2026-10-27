#------------------------------------------------------------------------------
# Outputs, which make sphinx-publish reads: terraform -chdir=terraform/docs output -raw <name>.
# bucket_name, distribution_id and publisher_role_arn are also the Publish workflow's
# DOCS_BUCKET, DOCS_DISTRIBUTION_ID and DOCS_AWS_ROLE_ARN repository variables.
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

output "publisher_role_arn" {
  description = "The IAM role that the Publish workflow's docs job assumes."
  value       = aws_iam_role.docs_publisher.arn
}
