# route53 environment-specific dns record
data "kubernetes_service" "ingress_nginx_controller" {
  metadata {
    name      = "common-ingress-nginx-controller"
    namespace = "kube-system"
  }
}
data "aws_elb_hosted_zone_id" "main" {}
data "aws_route53_zone" "root_domain" {
  name = var.root_domain
}

resource "aws_route53_zone" "environment_domain" {
  name = local.environment_domain
  tags = local.tags
}

resource "aws_route53_record" "environment_domain-ns" {
  zone_id = data.aws_route53_zone.root_domain.zone_id
  name    = aws_route53_zone.environment_domain.name
  type    = "NS"
  ttl     = "600"
  records = aws_route53_zone.environment_domain.name_servers
}


resource "aws_route53_record" "naked" {
  zone_id = aws_route53_zone.environment_domain.id
  name    = local.environment_domain
  type    = "A"

  alias {
    name                   = data.kubernetes_service.ingress_nginx_controller.status.0.load_balancer.0.ingress.0.hostname
    zone_id                = data.aws_elb_hosted_zone_id.main.id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "wildcard" {
  zone_id = aws_route53_zone.environment_domain.id
  name    = "*.${local.environment_domain}"
  type    = "A"

  alias {
    name                   = data.kubernetes_service.ingress_nginx_controller.status.0.load_balancer.0.ingress.0.hostname
    zone_id                = data.aws_elb_hosted_zone_id.main.id
    evaluate_target_health = true
  }
}
