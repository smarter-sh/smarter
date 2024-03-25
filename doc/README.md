# Technical Overview of this Architecture

Table of contents:

- [Developer Setup Guide](./CONTRIBUTING.md)
- [Django-React Integration](./DJANGO-REACT-INTEGRATION.md)
- [Example .env](./example-dot-env)
- [Code Management Best Practices](./GOOD_CODING_PRACTICE.md)
- [OpenAI JSON Examples](./OPENAI_JSON_EXAMPLES.md)
- [How to Get an OpenAI API Key](./OPENAI_API_GETTING_STARTED_GUIDE.md)
- [Semantic Versioning Guide](./SEMANTIC_VERSIONING.md)
- [Getting Started With AWS and Terraform](./TERRAFORM_GETTING_STARTED_GUIDE.md)
- [12-Factor Methodology](./Twelve_Factor_Methodology.md)

## Smarter Application Architecture

![Python Classes](https://github.com/QueriumCorp/smarter/blob/main/doc/img/smarter-codebase.png "Python Classes")

- **[Common](../smarter/smarter/common/)**: A collection of non-trivial helper functions ranging from interfaces to AWS backend services like SMTP email, to creation of expirable token-based urls. Of note is the [conf](../smarter/smarter/common/conf.py) module, built on Pydantic, which handles the copious amount of configuration data on which Smarter depends.
- **[lib](../smarter/smarter/lib/)**: configurations for backing services like Celery and Redis.
- **[Account](../smarter/smarter/apps/account/)**: A django app for managing enterprise accounts: user manager, permissions & roles, api keys, billing, payments, logs.
- **[Plugin](../smarter/smarter/apps/plugin/)**: Smarter's extensibility model for LLM's offering a [function calling](https://platform.openai.com/docs/guides/function-calling) feature in their API.
- **[Chat](../smarter/smarter/apps/chat/)**: Langchain implementation of LLM-agnostic chat-completion service with seamless integration to [Plugin](../smarter/smarter/apps/plugin/) and enterprise logging features.
- **[Chatbot](../smarter/smarter/apps/chatbot)**: customer chat api deployment manager for custom domain, api keys and skinning options.
- **[API](../smarter/smarter/apps/api/)**: Smarter's flagship product offering. Provides REST API endpoints for account management, plugin-enabled LLM requests, and customer api's.
- **[dashboard](../smarter/smarter/apps/dashboard/)**: The customer dashboard for performing prompt engineering development and testing, and for managing an enterprise account.

## Smarter API

TO DO: DOCUMENT THE PRIMARY API ENDPOINT FOR HANDLING LLM REQUESTS

## Deployment Infrastructure

TO DO: UPDATE ME PLEASE. WE MOVED TO KUBERNETES IN JAN-2024.

![AWS Diagram](https://github.com/QueriumCorp/smarter/blob/main/doc/img/aws-diagram.png "AWS Diagram")

- **[IAM](https://aws.amazon.com/iam/)**: a web service that helps you securely control access to AWS resources. With IAM, you can centrally manage permissions that control which AWS resources users can access. You use IAM to control who is authenticated (signed in) and authorized (has permissions) to use resources.
- **[S3](https://aws.amazon.com/s3/)**: Amazon Simple Storage Service is a service offered by Amazon Web Services that provides object storage through a web service interface. Amazon S3 uses the same scalable storage infrastructure that Amazon.com uses to run its e-commerce network.
- **[Certificate Manager](https://aws.amazon.com/certificate-manager/)**: handles the complexity of creating, storing, and renewing public and private SSL/TLS X.509 certificates and keys that protect your AWS websites and applications.
- **[CloudFront](https://aws.amazon.com/cloudfront/)**: Amazon CloudFront is a content delivery network (CDN) service built for high performance, security, and developer convenience.
- **[EKS](https://aws.amazon.com/eks/)**: Amazon Elastic Kubernetes Service (Amazon EKS) is a managed Kubernetes service to run Kubernetes in the AWS cloud and on-premises data centers. In the cloud, Amazon EKS automatically manages the availability and scalability of the Kubernetes control plane nodes responsible for scheduling containers, managing application availability, storing cluster data, and other key tasks.
- **[ECR](https://aws.amazon.com/ecr/)**: Amazon Elastic Container Registry (Amazon ECR) is a fully managed container registry offering high-performance hosting, so you can reliably deploy application images and artifacts anywhere.
- **[Route53](https://aws.amazon.com/route53/)**: a scalable and highly available Domain Name System service. Released on December 5, 2010.
- **[SES](https://aws.amazon.com/ses/)**: Amazon Simple Email Service (Amazon SES) lets you reach customers confidently without an on-premises Simple Mail Transfer Protocol (SMTP) email server using the Amazon SES API or SMTP interface.
- **[CloudWatch](https://aws.amazon.com/cloudwatch/)**: CloudWatch enables you to monitor your complete stack (applications, infrastructure, network, and services) and use alarms, logs, and events data to take automated actions and reduce mean time to resolution (MTTR).
