# The api of this platform, whose /api/v1/demos/stackademy/course-catalogue/ is the Stackademy course catalogue.
#
# This file is a string.Template: add_example_connections fills in the scheme and domain of the platform
# that applies it, from smarter_settings.environment_url and smarter_settings.environment_platform_domain,
# e.g. https://alpha.platform.example.com, or http://localhost:9357 in local development, so that the
# Stackademy ApiPlugin queries the api of its own platform.
#
# The course catalogue is password protected: this connection sends its apiKey Secret as a bearer
# token, and the course catalogue accepts the apiKey Secret of the Smarter account's smarter_test_api.
apiVersion: smarter.sh/v1
kind: ApiConnection
metadata:
  description: Api connection to this platform's Stackademy course catalogue, /api/v1/demos/stackademy/course-catalogue/
  name: smarter_test_api
  version: 0.1.0
  tags:
    - test
    - api
    - sample
  annotations:
    - smarter.sh/smarter-test-api/creator: QA Team
    - smarter.sh/smarter-test-api/purpose: unit testing
    - smarter.sh/smarter-test-api/release-date: 2024-06-15
    - smarter.sh/smarter-test-api/backward-compatibility: true
spec:
  connection:
    baseUrl: ${environment_platform_scheme}://${environment_platform_domain}
    timeout: 30
    authMethod: token
    apiKey: smarter_test_api
