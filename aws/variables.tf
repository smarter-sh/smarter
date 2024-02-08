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
variable "aws_profile" {
  description = "a valid AWS CLI profile located in $HOME/.aws/credentials"
  type        = string
  default     = "default"
}

variable "tags" {
  description = "A map of tags to add to all resources. Tags added to launch configuration or templates override these values."
  type        = map(string)
  default     = {}
}

###############################################################################
# OpenAI API parameters
###############################################################################
variable "openai_endpoint_image_n" {
  description = "FIX NOTE: what is this?"
  type        = number
  default     = 4
}
variable "openai_endpoint_image_size" {
  description = "Image output dimensions in pixels"
  type        = string
  default     = "1024x768"
}

variable "root_domain" {
  description = "a valid Internet domain name which you directly control using AWS Route53 in this account"
  type        = string
  default     = ""
}

variable "subdomain" {
  description = "a valid Internet domain name which you directly control using AWS Route53 in this account"
  type        = string
  default     = "dev"
}

variable "logging_level" {
  type    = string
  default = "INFO"
}

variable "eks_cluster_name" {
  description = "name of the existing EKS cluster"
  type        = string
}



###############################################################################
# Environment variables
###############################################################################
variable "DUMP_DEFAULTS" {
  description = "environment variable: value of the DUMP_DEFAULTS environment variable"
  type        = string
  default     = "false"
}
variable "OPENAI_API_KEY" {
  description = "environment variable: value of the OPENAI_API_KEY environment"
  type        = string
}
variable "PINECONE_API_KEY" {
  description = "environment variable: value of the PINECONE_API_KEY environment"
  type        = string
}
variable "PINECONE_ENVIRONMENT" {
  description = "environment variable: value of the PINECONE_ENVIRONMENT environment"
  type        = string
}
variable "GOOGLE_MAPS_API_KEY" {
  description = "environment variable: value of the GOOGLE_MAPS_API_KEY environment"
  type        = string
}

variable "PRODUCTION_DATABASE_USER" {
  description = "value of the PRODUCTION_DATABASE_USER environment"
}
variable "PRODUCTION_DATABASE_PASSWORD" {
  description = "value of the PRODUCTION_DATABASE_PASSWORD environment"
}
variable "PRODUCTION_DATABASE_HOST" {

}
variable "PRODUCTION_DATABASE_PORT" {

}
