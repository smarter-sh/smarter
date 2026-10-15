# The Stackademy course catalogue test api, /api/v1/tests/stackademy/course-catalogue/, of this platform.
#
# This file is a string.Template: create_stackademy fills in the scheme and domain of the platform
# that applies it, from smarter_settings.environment_url and smarter_settings.environment_platform_domain,
# e.g. https://alpha.platform.example.com, or http://localhost:9357 in local development, so that the
# Stackademy ApiPlugin queries the api of its own platform.
apiVersion: smarter.sh/v1
kind: ApiConnection
metadata:
  description: Api connection Stackademy courses catalogue /api/v1/tests/stackademy/course-catalogue/
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
    baseUrl: ${environment_platform_scheme}://${environment_platform_domain}/api/v1/tests
    timeout: 30
    authMethod: none
