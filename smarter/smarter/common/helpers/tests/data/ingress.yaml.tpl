apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${domain}
  namespace: ${environment_namespace}
  annotations:
    kubernetes.io/tls-acme: "true"
    cert-manager.io/cluster-issuer: ${cluster_issuer}
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.middlewares: ${environment_namespace}-cors@kubernetescrd,${environment_namespace}-https-redirect@kubernetescrd
  labels:
    app.kubernetes.io/application-group: ${ app_name }
    app.kubernetes.io/name: ${ app_name }
spec:
  ingressClassName: traefik
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
