apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: ${cluster_issuer}
    kubernetes.io/ingress.class: nginx
  name: ${domain}
  namespace: ${environment_namespace}
spec:
  ingressClassName: "default"
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
    - host: "*.${domain}"
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
