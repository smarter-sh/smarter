#--------------------------------------------------------------
# Deploy containerized application to an existing Kubernetes cluster
#--------------------------------------------------------------

# resource "kubernetes_manifest" "deployment" {
#   manifest = yamldecode(data.template_file.deployment.rendered)
# }

# 3. horizontal scaling policy
# 4. vertical scaling policy
# 9. mysql secret
locals {

  smarter_mysql_database = substr("${var.shared_resource_identifier}_${local.environment}", -64, -1)
  smarter_mysql_username = substr("${var.shared_resource_identifier}_${local.environment}", -32, -1)
  smarter_mysql_host     = "mysql.service.lawrencemcdaniel.com"
  smarter_mysql_port     = "3306"

}

resource "random_password" "mysql_smarter" {
  length           = 16
  special          = true
  override_special = "_%@"
  keepers = {
    version = "1"
  }
}


resource "kubernetes_secret" "mysql_smarter" {
  metadata {
    name      = "mysql-smarter"
    namespace = local.environment_namespace
  }

  data = {
    SMARTER_MYSQL_DATABASE = local.smarter_mysql_database
    SMARTER_MYSQL_USERNAME = local.smarter_mysql_username
    SMARTER_MYSQL_PASSWORD = random_password.mysql_smarter.result
    MYSQL_HOST             = local.smarter_mysql_host
    MYSQL_PORT             = local.smarter_mysql_port
  }

  depends_on = [kubernetes_namespace.smarter]
}
