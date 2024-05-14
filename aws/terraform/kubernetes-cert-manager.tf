locals {
  template_issuer_platform = templatefile("${path.module}/templates/issuer.yml.tpl", {
    root_domain    = var.root_domain
    environment    = local.environment
    domain         = local.environment_platform_domain
    namespace      = "cert-manager"
    aws_region     = var.aws_region
    hosted_zone_id = data.aws_route53_zone.environment_platform_domain.zone_id
  })
  template_issuer_api = templatefile("${path.module}/templates/issuer.yml.tpl", {
    root_domain    = var.root_domain
    environment    = local.environment
    domain         = local.environment_api_domain
    namespace      = "cert-manager"
    aws_region     = var.aws_region
    hosted_zone_id = data.aws_route53_zone.environment_api_domain.zone_id
  })
}

data "aws_route53_zone" "environment_api_domain" {
  name = local.environment_api_domain
}

data "aws_route53_zone" "environment_platform_domain" {
  name = local.environment_platform_domain
}

resource "kubernetes_manifest" "issuer_platform" {
  manifest = yamldecode(local.template_issuer_platform)

  depends_on = [
    aws_route53_zone.environment_platform_domain,
    aws_route53_record.environment_platform_domain-ns,
    kubernetes_namespace.smarter,
    kubernetes_manifest.platform_ingress,
  ]
}

resource "kubernetes_manifest" "issuer_api" {
  manifest = yamldecode(local.template_issuer_api)

  depends_on = [
    aws_route53_zone.environment_platform_domain,
    aws_route53_record.environment_platform_domain-ns,
    kubernetes_namespace.smarter,
    kubernetes_manifest.api_ingress
  ]
}
