#--------------------------------------------------------------
# Deploy containerized application to an existing Kubernetes cluster
#--------------------------------------------------------------

# resource "kubernetes_manifest" "deployment" {
#   manifest = yamldecode(data.template_file.deployment.rendered)
# }

# 3. horizontal scaling policy
# 4. vertical scaling policy
# 9. mysql secret

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
    SMARTER_MYSQL_DATABASE = local.mysql_database
    SMARTER_MYSQL_USERNAME = local.mysql_username
    SMARTER_MYSQL_PASSWORD = random_password.mysql_smarter.result
    MYSQL_HOST             = var.mysql_host
    MYSQL_PORT             = var.mysql_port
  }

  depends_on = [kubernetes_namespace.smarter]
}

resource "random_password" "smarter_admin_password" {
  length           = 16
  special          = true
  override_special = "_%@"
  keepers = {
    version = "1"
  }
}

resource "kubernetes_secret" "smarter_admin_password" {
  metadata {
    name      = "smarter-admin"
    namespace = local.environment_namespace
  }

  data = {
    SMARTER_ADMIN_USERNAME = "admin"
    SMARTER_ADMIN_PASSWORD = random_password.smarter_admin_password.result
    SMARTER_LOGIN_URL      = "https://${local.environment_domain}/api-auth/login/"
  }

  depends_on = [kubernetes_namespace.smarter]
}


resource "random_password" "django_secret_key" {
  length           = 16
  special          = true
  override_special = "_%@"
  keepers = {
    version = "1"
  }
}

resource "kubernetes_secret" "django_secret_key" {
  metadata {
    name      = "smarter-django-secret-key"
    namespace = local.environment_namespace
  }

  data = {
    SECRET_KEY = random_password.django_secret_key.result
  }

  depends_on = [kubernetes_namespace.smarter]
}
