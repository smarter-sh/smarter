apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  generation: 1
  name: ${domain}
  namespace: ${environment_namespace}
  annotations:
    kubernetes.io/tls-acme: "true"
    cert-manager.io/cluster-issuer: ${cluster_issuer}
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    # No Traefik cors middleware: it answers CORS preflight requests itself, with a fixed list of
    # origins and headers, so Django, whose CORS middleware applies the platform's settings and each
    # LLMClient's spec.config.allowedOrigins (smarter.apps.llmclient.cors), would never see them.
    traefik.ingress.kubernetes.io/router.middlewares: ${environment_namespace}-https-redirect@kubernetescrd
  labels:
    app.kubernetes.io/application-group: ${app_name}
    app.kubernetes.io/name: ${app_name}
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
  tls:
  - hosts:
    - ${domain}
    secretName: ${domain}-tls
