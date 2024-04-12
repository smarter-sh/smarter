locals {
  template_issuer = templatefile("${path.module}/templates/issuer.yml.tpl", {
    root_domain    = var.root_domain
    environment    = local.environment
    domain         = local.environment_platform_domain
    namespace      = "cert-manager"
    aws_region     = var.aws_region
    hosted_zone_id = aws_route53_zone.environment_platform_domain.zone_id
  })
}

resource "kubernetes_manifest" "issuer" {
  manifest = yamldecode(local.template_issuer)

  depends_on = [
    aws_route53_zone.environment_platform_domain,
    aws_route53_record.environment_platform_domain-ns,
    kubernetes_namespace.smarter,
    kubernetes_manifest.platform_ingress,
    kubernetes_manifest.api_ingress
  ]
}
