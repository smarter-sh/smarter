
# 1. namespace
resource "kubernetes_namespace" "smarter" {
  metadata {
    name = local.environment_namespace
  }
}

