---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: ${domain}
spec:
  acme:
    email: no-reply@${root_domain}
    privateKeySecretRef:
      name: ${domain}
    server: https://acme-v02.api.letsencrypt.org/directory
    solvers:
      - http01:
          ingress:
            class: nginx
      - dns01:
          # hosted Zone ID for for the environment domain.
          route53:
            region: ${aws_region}
            hostedZoneID: ${hosted_zone_id}
            ambientCredentials: true
