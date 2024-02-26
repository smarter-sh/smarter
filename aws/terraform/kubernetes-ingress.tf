locals {
  template_cluster_issuer = templatefile("${path.module}/templates/cluster-issuer.yml.tpl", {
    root_domain        = var.root_domain
    environment_domain = local.environment_domain
    aws_region         = var.aws_region
    hosted_zone_id     = aws_route53_zone.environment_domain.zone_id
  })

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

# resource "kubernetes_manifest" "cluster-issuer" {
#   manifest = yamldecode(local.template_cluster_issuer)

#   depends_on = [
#     aws_route53_zone.environment_domain,
#     kubernetes_namespace.smarter,
#     kubernetes_manifest.ingress,
#   ]
# }
