apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: ${cluster_issuer}
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/affinity: cookie
    nginx.ingress.kubernetes.io/backend-protocol: HTTP
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-buffer-size: 256k
    nginx.ingress.kubernetes.io/proxy-buffers: 4 512k
    nginx.ingress.kubernetes.io/proxy-busy-buffers-size: 512k
    nginx.ingress.kubernetes.io/session-cookie-expires: "172800"
    nginx.ingress.kubernetes.io/session-cookie-max-age: "172800"
    nginx.ingress.kubernetes.io/session-cookie-name: ${environment_namespace}_sticky_session
  name: ${domain}
  namespace: ${environment_namespace}
spec:
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
