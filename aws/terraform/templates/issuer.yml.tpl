---
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-issuer
  namespace: ${namespace}
spec:
  acme:
    email: no-reply@${root_domain}
    privateKeySecretRef:
      name: ${environment_domain}
    server: https://acme-v02.api.letsencrypt.org/directory
    solvers:
      - dns01:
          # hosted Zone ID for for the environment domain.
          route53:
            region: ${aws_region}
            hostedZoneID: ${hosted_zone_id}
