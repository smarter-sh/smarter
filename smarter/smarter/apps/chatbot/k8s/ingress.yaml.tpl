apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: ${cluster_issuer}
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://${domain}"
    nginx.ingress.kubernetes.io/cors-allow-methods: "PUT, GET, POST, OPTIONS, DELETE"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,X-CustomHeader,X-LANG,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,X-Api-Key,X-Device-Id,Access-Control-Allow-Origin,X-CSRFToken"
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
    nginx.ingress.kubernetes.io/use-forwarded-headers: "true"
    nginx.ingress.kubernetes.io/compute-full-forwarded-for: "true"
    nginx.ingress.kubernetes.io/use-proxy-protocol: "true"
    nginx.ingress.kubernetes.io/proxy-real-ip-cidr: "0.0.0.0/0"
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
      secretName: ${domain}-tls
