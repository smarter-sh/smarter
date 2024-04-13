apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: ${ca_data}
    server: ${server_endpoint}
  name: ${cluster_name}
contexts:
- context:
    cluster: ${cluster_name}
    user: default
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: default
  user: {}
