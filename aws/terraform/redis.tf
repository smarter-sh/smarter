
resource "helm_release" "redis" {
  name             = "redis"
  namespace        = local.environment_namespace
  create_namespace = false

  chart      = "redis"
  repository = "bitnami"
  version    = "~> 19.0"


  # https://github.com/bitnami/charts/blob/main/bitnami/wordpress/values.yaml
  # or
  # helm show values bitnami/wordpress
  values = [
    <<-EOF
    global:
      redis:
        password: "smarter"
    replica:
      replicaCount: 0
    master:
      resources:
        requests:
          memory: "64Mi"
          cpu: "250m"
        limits:
          memory: "128Mi"
          cpu: "500m"
    EOF
  ]

  depends_on = [kubernetes_namespace.smarter]

}
