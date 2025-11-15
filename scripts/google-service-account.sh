# --------------------------------------------
# Script to convert a Google service account JSON file to a base64 string
# --------------------------------------------
base64 -i service-account.json | tr -d '\n' > service-account.b64
