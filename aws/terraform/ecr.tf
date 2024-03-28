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

resource "aws_ecr_lifecycle_policy" "smarter" {
  repository = aws_ecr_repository.smarter.name

  policy = <<EOF
      {
        "rules": [
          {
            "rulePriority": 1,
            "description": "Keep last 10 images",
            "selection": {
              "tagStatus": "any",
              "countType": "imageCountMoreThan",
              "countNumber": 10
            },
            "action": {
              "type": "expire"
            }
          }
        ]
      }
      EOF
}
