#------------------------------------------------------------------------------
# The Publish workflow's access to the docs site.
#
# After a release is deployed, publish.yml's docs job uploads the site and
# invalidates CloudFront. It signs in with GitHub's OIDC token, so no AWS key
# is stored in GitHub, and only a job in this repository's "docs" environment
# can assume the role. That environment is limited to main in the
# repository's settings. The same as smarter-python, smarter-types and
# cache-results.
#------------------------------------------------------------------------------

# GitHub's OIDC provider is one per AWS account and already exists, shared by
# every repository's workflows, each with a role of its own. This stack only
# reads it.
data "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "docs_publisher_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:environment:${var.github_environment}"]
    }
  }
}

resource "aws_iam_role" "docs_publisher" {
  name               = "smarter-docs-publisher"
  description        = "The smarter Publish workflow, publishing ${var.domain_name}"
  assume_role_policy = data.aws_iam_policy_document.docs_publisher_trust.json
}

# Exactly what make sphinx-publish does: sync the bucket, and invalidate the distribution.
data "aws_iam_policy_document" "docs_publisher" {
  statement {
    sid       = "ListTheBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.docs.arn]
  }

  statement {
    sid       = "SyncTheSite"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.docs.arn}/*"]
  }

  statement {
    sid       = "InvalidateTheDistribution"
    actions   = ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"]
    resources = [aws_cloudfront_distribution.docs.arn]
  }
}

resource "aws_iam_role_policy" "docs_publisher" {
  name   = "publish-docs"
  role   = aws_iam_role.docs_publisher.id
  policy = data.aws_iam_policy_document.docs_publisher.json
}
