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

resource "aws_route53_zone" "environment_platform_domain" {
  name = local.environment_platform_domain
  tags = local.tags
}

resource "aws_route53_record" "environment_platform_domain-ns" {
  zone_id = data.aws_route53_zone.root_domain.zone_id
  name    = aws_route53_zone.environment_platform_domain.name
  type    = "NS"
  ttl     = "600"
  records = aws_route53_zone.environment_platform_domain.name_servers
}


resource "aws_route53_record" "naked" {
  zone_id = aws_route53_zone.environment_platform_domain.id
  name    = local.environment_platform_domain
  type    = "A"

  alias {
    name                   = data.kubernetes_service.ingress_nginx_controller.status.0.load_balancer.0.ingress.0.hostname
    zone_id                = data.aws_elb_hosted_zone_id.main.id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "wildcard" {
  zone_id = aws_route53_zone.environment_platform_domain.id
  name    = "*.${local.environment_platform_domain}"
  type    = "A"

  alias {
    name                   = data.kubernetes_service.ingress_nginx_controller.status.0.load_balancer.0.ingress.0.hostname
    zone_id                = data.aws_elb_hosted_zone_id.main.id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "aws_ses_domain_identity" {
  zone_id = aws_route53_zone.environment_platform_domain.zone_id
  name    = "_amazonses.${local.environment_platform_domain}"
  type    = "TXT"
  ttl     = "600"
  records = [aws_ses_domain_identity.environment_platform_domain.verification_token]
}

resource "aws_route53_record" "environment_platform_domain_amazonses_dkim_record" {
  count   = 3
  zone_id = aws_route53_zone.environment_platform_domain.zone_id
  name    = "${aws_ses_domain_dkim.environment_platform_domain.dkim_tokens[count.index]}._domainkey"
  type    = "CNAME"
  ttl     = "600"
  records = ["${aws_ses_domain_dkim.environment_platform_domain.dkim_tokens[count.index]}.dkim.amazonses.com"]
}
