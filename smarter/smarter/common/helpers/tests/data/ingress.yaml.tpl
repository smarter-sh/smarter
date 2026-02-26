apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/tls-acme: "true"
    cert-manager.io/cluster-issuer: ${cluster_issuer}
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.middlewares: ${environment_namespace}-cors@kubernetescrd,${environment_namespace}-https-redirect@kubernetescrd

  name: ${domain}
  namespace: ${environment_namespace}
spec:
  ingressClassName: default
  rules:
    - host: ${domain}
      http:
        paths:
          - backend:
              service:
                name: ${service_name}
                port:
                  number: 8000
            path: /
            pathType: Prefix
  # -----------------------------------------------------
  # automagically create tls/ssl cert via cert-manager
  # https://cert-manager.io/docs/usage/ingress/
  # -----------------------------------------------------
  tls:
    - hosts:
        - ${domain}
        - "*.${domain}"
      secretName: ${domain}-tls
