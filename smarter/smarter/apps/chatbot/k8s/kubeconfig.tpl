apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: ${ca_data}
    server: ${server_endpoint}
  name: apps-hosting-service
contexts:
- context:
    cluster: apps-hosting-service
    user: apps-hosting-service
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: default
  user: {}
