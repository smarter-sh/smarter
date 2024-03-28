#------------------------------------------------------------------------------
# written by: Miguel Afonso
#             https://www.linkedin.com/in/mmafonso/
#
# date: Feb-2024
#
# usage: create a new smarter environment
#------------------------------------------------------------------------------
locals {
  global_vars = read_terragrunt_config(find_in_parent_folders("global.hcl"))

  # environment vars
  environment           = "prod"
  subdomain             = "platform"
}

# Terragrunt will copy the Terraform configurations specified by the source parameter, along with any files in the
# working directory, into a temporary folder, and execute your Terraform commands in that folder.

terraform {
  source = "..//terraform"
}

# Include all settings from the root terragrunt.hcl file
include {
  path = find_in_parent_folders()
}

# These are the variables we have to pass in to use the module specified in the terragrunt configuration above
inputs = merge(
  local.global_vars.locals,
  {
    environment  = local.environment
    subdomain    = local.subdomain
  }
)
