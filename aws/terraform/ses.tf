#------------------------------------------------------------------------------
# written by: Lawrence McDaniel
#             https://lawrencemcdaniel.com
#
# date:   apr-2023
#
# usage:  create AWS SES registered domain
#         create DKIM records for the registered domain
#
# see: https://stackoverflow.com/questions/52850212/terraform-aws-ses-credential-resource
#
#------------------------------------------------------------------------------

resource "aws_ses_domain_identity" "environment_platform_domain" {
  domain = local.environment_platform_domain
}

resource "aws_ses_domain_dkim" "environment_platform_domain" {
  domain = aws_ses_domain_identity.environment_platform_domain.domain
}
