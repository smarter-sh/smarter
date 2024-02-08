#------------------------------------------------------------------------------
# written by: Lawrence McDaniel
#             https://lawrencemcdaniel.com/
#
# date:   feb-2024
#
# usage:  build and upload an environment-specific Docker image
#         to AWS Elastic Container Registry (ECR)
#------------------------------------------------------------------------------
locals {
  ecr_repo          = var.shared_resource_identifier
  ecr_build_path    = "${path.module}/docker"
  ecr_build_script  = "${local.ecr_build_path}/build.sh"
  docker_files_hash = join(",", [for f in fileset("./docker", "*.*") : filesha256("./docker/${f}")])
  python_files_hash = join(",", [for f in fileset("../python", "*.*") : filesha256("../python/${f}")])
}

resource "aws_ecr_repository" "smarter" {
  name                 = local.ecr_repo
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
  tags = var.tags

}

###############################################################################
# Docker Build and Push
###############################################################################
resource "null_resource" "smarter" {
  triggers = {
    docker_files    = local.docker_files_hash
    python_files    = local.python_files_hash     # FIX ME
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash"]
    command     = local.ecr_build_script

    environment = {
      REPO_NAME      = local.ecr_repo
      BUILD_PATH     = local.ecr_build_path
      CONTAINER_NAME = local.ecr_repo
      AWS_REGION     = var.aws_region
      AWS_ACCOUNT_ID = var.aws_account_id
    }
  }

  depends_on = [aws_ecr_repository.smarter]
}
