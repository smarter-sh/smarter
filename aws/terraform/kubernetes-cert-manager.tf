locals {
  template_issuer = templatefile("${path.module}/templates/issuer.yml.tpl", {
    root_domain        = var.root_domain
    environment_domain = local.environment_domain
    namespace          = local.environment_namespace
    aws_region         = var.aws_region
    hosted_zone_id     = aws_route53_zone.environment_domain.zone_id
  })
}

resource "kubernetes_manifest" "issuer" {
  manifest = yamldecode(local.template_issuer)

  depends_on = [
    aws_route53_zone.environment_domain,
    aws_route53_record.naked,
    aws_route53_record.wildcard,
    aws_route53_record.environment_domain-ns,
    kubernetes_namespace.smarter,
    kubernetes_manifest.ingress,
  ]
}
