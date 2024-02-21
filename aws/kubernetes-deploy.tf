
locals {
  env_script = "${path.module}/../scripts/env.sh"

  template_db_init = templatefile("${path.module}/templates/db-init.sh.tpl", {
    mysql_user             = var.PRODUCTION_DATABASE_USER
    mysql_password         = var.PRODUCTION_DATABASE_PASSWORD
    mysql_host             = var.PRODUCTION_DATABASE_HOST
    mysql_port             = var.PRODUCTION_DATABASE_PORT
    mysql_database         = local.mysql_database
    smarter_mysql_user     = local.mysql_username
    smarter_mysql_password = random_password.mysql_smarter.result
    admin_username         = "admin"
    admin_email            = "admin@smarter.sh"
    admin_password         = random_password.mysql_smarter.result
  })
}

resource "kubernetes_service" "smarter" {
  metadata {
    name      = var.shared_resource_identifier
    namespace = kubernetes_namespace.smarter.metadata[0].name
  }

  spec {
    selector = {
      "app.kubernetes.io/name" = var.shared_resource_identifier
    }

    port {
      port        = 8000
      target_port = 8000
    }

    type = "LoadBalancer"
  }
}

resource "kubernetes_deployment" "smarter" {
  lifecycle {
    create_before_destroy = true
  }

  metadata {
    name      = var.shared_resource_identifier
    namespace = kubernetes_namespace.smarter.metadata[0].name
    labels = {
      App = var.shared_resource_identifier
    }
  }

  spec {
    replicas = 2

    selector {
      match_labels = {
        "app.kubernetes.io/name" = var.shared_resource_identifier
      }
    }

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name" = var.shared_resource_identifier
        }
      }

      spec {
        container {
          image = local.ecr_repository_image
          name  = var.shared_resource_identifier

          port {
            container_port = 8000
          }

          env {
            name  = "ROOT_DOMAIN"
            value = var.root_domain
          }
          env {
            name  = "AWS_ACCESS_KEY_ID"
            value = var.AWS_ACCESS_KEY_ID
          }
          env {
            name  = "AWS_SECRET_ACCESS_KEY"
            value = var.AWS_SECRET_ACCESS_KEY
          }
          env {
            name  = "AWS_REGION"
            value = var.aws_region
          }
          env {
            name  = "ENVIRONMENT"
            value = "prod"
          }
          env {
            name  = "DEBUG_MODE"
            value = "true"
          }
          env {
            name  = "DUMP_DEFAULTS"
            value = var.DUMP_DEFAULTS
          }
          env {
            name  = "MYSQL_HOST"
            value = var.mysql_host
          }
          env {
            name  = "MYSQL_PORT"
            value = var.mysql_port
          }
          env {
            name  = "MYSQL_DATABASE"
            value = local.mysql_database
          }
          env {
            name  = "MYSQL_USER"
            value = local.mysql_username
          }
          env {
            name  = "MYSQL_PASSWORD"
            value = random_password.mysql_smarter.result
          }
          env {
            name  = "OPENAI_API_KEY"
            value = var.OPENAI_API_KEY
          }
          env {
            name  = "PINECONE_API_KEY"
            value = var.PINECONE_API_KEY
          }
          env {
            name  = "PINECONE_ENVIRONMENT"
            value = var.PINECONE_ENVIRONMENT
          }
          env {
            name  = "GOOGLE_MAPS_API_KEY"
            value = var.GOOGLE_MAPS_API_KEY
          }
          env {
            name  = "SECRET_KEY"
            value = random_password.django_secret_key.result
          }
        }
      }
    }
  }
  depends_on = [
    kubernetes_namespace.smarter,
    aws_route53_zone.environment_domain
  ]
}

resource "kubernetes_job" "db_migration" {
  metadata {
    name      = "${var.shared_resource_identifier}-job"
    namespace = kubernetes_namespace.smarter.metadata[0].name
  }

  spec {
    template {
      metadata {
        labels = {
          "app.kubernetes.io/name" = "${var.shared_resource_identifier}-job"
        }
      }

      spec {
        container {
          name  = "${var.shared_resource_identifier}-db-job"
          image = local.ecr_repository_image

          command = ["/bin/sh", "-c"]
          args    = [local.template_db_init]

          env {
            name  = "ROOT_DOMAIN"
            value = var.root_domain
          }
          env {
            name  = "AWS_ACCESS_KEY_ID"
            value = var.AWS_ACCESS_KEY_ID
          }
          env {
            name  = "AWS_SECRET_ACCESS_KEY"
            value = var.AWS_SECRET_ACCESS_KEY
          }
          env {
            name  = "AWS_REGION"
            value = var.aws_region
          }
          env {
            name  = "ENVIRONMENT"
            value = "prod"
          }
          env {
            name  = "DEBUG_MODE"
            value = "true"
          }
          env {
            name  = "MYSQL_HOST"
            value = var.mysql_host
          }
          env {
            name  = "MYSQL_PORT"
            value = var.mysql_port
          }
          env {
            name  = "MYSQL_DATABASE"
            value = local.mysql_database
          }
          env {
            name  = "MYSQL_USER"
            value = local.mysql_username
          }
          env {
            name  = "MYSQL_PASSWORD"
            value = random_password.mysql_smarter.result
          }
          env {
            name  = "SECRET_KEY"
            value = random_password.django_secret_key.result
          }
        }

        restart_policy = "Never"
      }
    }

    backoff_limit = 4
  }

  depends_on = [
    kubernetes_deployment.smarter
  ]
}
