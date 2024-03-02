#------------------------------------------------------------------------------
# written by: Lawrence McDaniel
#             https://lawrencemcdaniel.com/
#
# date:   feb-2024
#
# usage:  AWS Elastic Container Registry (ECR)
#------------------------------------------------------------------------------

resource "aws_ecr_repository" "smarter" {
  name                 = local.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
  tags = local.tags

}
