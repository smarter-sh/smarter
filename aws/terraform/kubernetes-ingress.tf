locals {
  template_ingress = templatefile("${path.module}/templates/ingress.yaml.tpl", {
    environment_domain    = local.environment_domain
    environment_namespace = local.environment_namespace
    service_name          = var.shared_resource_identifier
  })

}


resource "kubernetes_manifest" "ingress" {
  manifest = yamldecode(local.template_ingress)

  depends_on = [
    aws_route53_zone.environment_domain
  ]
}
