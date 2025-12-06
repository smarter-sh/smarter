Helper Overview for AWS
===========================

This section provides documentation for the AWS helper classes available in the Smarter framework.
These helpers facilitate interactions with the AWS services that Smarter supports, providing layers of abstraction
for common tasks, like setting up DNS records, managing SSL certificates, and configuring cloud resources.

All AWS helper functions are available through a Singleton instance of the `AWSInfrastructureConfig` class.

.. code-block:: python

   from smarter.common.helpers.helpers import aws_helper

   aws_helper.route53.get_or_create_hosted_zone("example.com")

returns a dictionary similar to:

.. code-block:: json

            {
            "HostedZone": {
                "Id": "/hostedzone/Z148QEXAMPLE8V",
                "Name": "example.com.",
                "CallerReference": "my hosted zone",
                "Config": {
                    "Comment": "This is my hosted zone",
                    "PrivateZone": false
                },
                "ResourceRecordSetCount": 2
            },
            "DelegationSet": {
                "NameServers": [
                    "ns-2048.awsdns-64.com",
                    "ns-2049.awsdns-65.net",
                    "ns-2050.awsdns-66.org",
                    "ns-2051.awsdns-67.co.uk"
                ]
            }
        }
