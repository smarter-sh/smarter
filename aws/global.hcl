#------------------------------------------------------------------------------
# written by: Lawrence McDaniel
#             https://lawrencemcdaniel.com/
#
# date: Feb-2024
#
# usage: create global parameters, exposed to all
#        Terragrunt modules in this repository.
#------------------------------------------------------------------------------
locals {

    ###############################################################################
    # AWS CLI parameters
    ###############################################################################
    aws_account_id             = get_env("AWS_ACCOUNT_ID", "SET-ME-PLEASE")
    aws_profile                = get_env("AWS_PROFILE", "default")
    aws_region                 = get_env("AWS_REGION", "us-east-2")
    root_domain                = get_env("ROOT_DOMAIN", "smarter.sh")

    shared_resource_identifier = "smarter"
    eks_cluster_name           = "apps-hosting-service"
    mysql_host                 = "mysql.service.lawrencemcdaniel.com"
    mysql_port                 = "3306"
    tags = {
      "terraform"                 = "true",
      "project"                   = "Querium Smarter"
      "contact"                   = "Lawrence McDaniel - https://lawrencemcdaniel.com/"
      "smarter/root_domain"       = local.root_domain
      "smarter/eks_cluster_name"  = local.eks_cluster_name
      "smarter/mysql_host"        = local.mysql_host
    }

    ###############################################################################
    # OpenAI API parameters
    ###############################################################################
    openai_endpoint_image_n    = 4
    openai_endpoint_image_size = "1024x768"


    ###############################################################################
    # CloudWatch logging parameters
    ###############################################################################
    logging_level = "INFO"

}

inputs = {
    aws_account_id             = local.aws_account_id
    aws_profile                = local.aws_profile
    aws_region                 = local.aws_region
    root_domain                = local.root_domain
    shared_resource_identifier = local.shared_resource_identifier
    eks_cluster_name           = local.eks_cluster_name
    mysql_host                 = local.mysql_host
    mysql_port                 = local.mysql_port
    tags                       = local.tags
}
