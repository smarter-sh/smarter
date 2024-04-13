#------------------------------------------------------------------------------
# written by: Lawrence McDaniel
#             https://lawrencemcdaniel.com/
#
# date:       sep-2023
#
# usage:      all Terraform variable declarations
#------------------------------------------------------------------------------
variable "shared_resource_identifier" {
  description = "A common identifier/prefix for resources created for this demo"
  type        = string
  default     = "openai"
}

variable "aws_account_id" {
  description = "12-digit AWS account number"
  type        = string
}
variable "aws_region" {
  description = "A valid AWS data center region code"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "A map of tags to add to all resources. Tags added to launch configuration or templates override these values."
  type        = map(string)
  default     = {}
}

variable "root_domain" {
  description = "a valid Internet domain name which you directly control using AWS Route53 in this account"
  type        = string
  default     = ""
}

variable "platform_subdomain" {
  description = "a valid Internet domain name which you directly control using AWS Route53 in this account"
  type        = string
  default     = "alpha"
}

variable "api_subdomain" {
  description = "a valid Internet domain name which you directly control using AWS Route53 in this account"
  type        = string
  default     = "alpha"
}

variable "environment" {
  description = "the environment name (e.g. local, alpha, beta, next, prod)"
  type        = string
  default     = "local"
}

variable "eks_cluster_name" {
  description = "name of the existing EKS cluster"
  type        = string
}

variable "mysql_host" {
  description = "hostname of the existing MySQL database"
  type        = string
}

variable "mysql_port" {
  description = "port number of the existing MySQL database"
  type        = string
  default     = "3306"
}
