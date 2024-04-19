# ChatBot API's

ChatBot's are accessible via REST API. End points to deployed ChatBots are publicly accessible unless the customer has chosen to attach a Smarter API key. Http requests should substantially conform this command structure:

```console
curl --location 'https://example.3141-5926-5359.api.smarter.sh/chatbot/' \
--header 'x-api-key: api-key-string-of-around-64-hashed-characters' \
--header 'Content-Type: application/json' \
--data '{
    "messages": [
        {
            "role": "user",
            "content": "what is FMLA?"
        }
    ],
    "chat_history": [
        {
            "message": "Hello, How can I help you?",
            "direction": "incoming",
            "sentTime": "11/16/2023, 5:53:32 PM",
            "sender": "system"
        }
    ]
}'
```

## Domain Name Resolution

The Smarter application stack provides consistent behavior for either of three different domain name styles

- Default ChatBot domain names: [subdomain].[####-####-####].[environment].smarter.sh/chatbot/
- Customer's custom domain names: [subdomain].example.com/chatbot/
- The Smarter API: /api/v0/chatbots/[int]/[ChatBot.name]

Secondarily, it also needs to gracefully adapt to alternatives like `localhost`, `127.0.0.1` and conjured up names used in unit tests.

## URL Parsing and Routing

In light of the multiple naming schemes, mapping hosts and urls to a ChatBot is not trivial. Note the following code resources for working with chatbot urls:

- `smarter.apps.chatbot.models.ChatBotHelper`: Maps a url to its ChatBot, Plugin list, Account and User objects.
- `smarter.lib.django.validators.SmarterValidator`: Low-level url parsing features.
- `smarter.common.conf.settings`: A singleton that provides settings values for the environment and base customer API domains.

### Default Domain

The default domain for each ChatBot is accessible regardless of whether the customer has also implemented a custom domain.

example: https://example.3141-5926-5359.beta.api.smarter.sh/chatbot/

where

- `/chatbot/` is a URL endpoint defined in smarter/urls.py and resolves to a Django View that invoke Chat with a List of Smarter Plugin objects.

- `example' == ChatBot.name`
- `3141-5926-5359 == ChatBot.account.account_number`
- `beta.api.smarter.sh == smarter_settings.customer_api_domain`

### Custom Domain

Customers can configure a custom domain for their account, mapping individual chatbots to DNS subdomain records aliased to the master Kubernetes ingress controller for the platform. Smarter provides `manage.py` admin commands for managing the complete lifecycle of customer custom domain recourses.

example: https://sales.api.smarter.querium.com/chatbot/
where

- `api.smarter.querium.com == chatbot.custom_domain`: A ChatBotCustomDomain object
- `sales`: is a verified A record (ie a subdomain) in the AWS Hosted zone for the customer domain
- `ChatBotCustomDomain.is_verified == True`: An asynchronous task verifies the domain NS records.

The ChatBot instance hostname is determined by the following logic: `chatbot.hostname == ChatBot.custom_domain` once the following conditions are satisfied:

- `ChatBotCustomDomain.is_verified == True`. An asynchronous task verifies the domain NS records.
- `ChatBot.deployed==True`. This is a customer-managed setting.

## Django Application Configuration

There are multiple Django configuration implications due to the default customer domain naming style, as well as the fact that custom domains need to be treated as if they were in fact the Django platform `ENVIRONMENT_DOMAIN`. For example, `beta.smarter.sh`. These domain naming styles require customizations to url routing within Django, as well as to `ALLOWED_HOSTS`, CORS, CSRF, ssl-certificates, and multiple kinds of Kubernetes resources.

### ALLOWED_HOSTS

For Django to accept http requests from any domain, it must be included in Django's `ALLOWED_HOSTS` settings which is managed by Django middleware that we've subclassed as `smarter.apps.chatbot.middleware.security.SecurityMiddleware` in order to append API domain names to `ALLOWED_HOSTS` at run time.

### CORS

We subclassed the standard `corsheaders` as `smarter.apps.chatbot.middleware.cors.CorsMiddleware` in order to performantly append API domain names to `CORS_ALLOWED_ORIGINS` at run time..

### Cross-Site Request Forgery

We subclassed Django's csrf library as `smarter.apps.chatbot.middleware.csrf.CsrfViewMiddleware` in order to append API domain names to `CSRF_TRUSTED_ORIGINS` at run time.

### TLS/SSL Certificates

The certificates issued and managed by `cert-manager` in Kubernetes for each environment only support the first level of subdomain, implemented as a wildcard. For example, `*.beta.api.smarter.sh`. Therefore, API domains like for example, `example.3141-5926-5359.api.smarter.sh`, fall outside of this scheme. Smarter therefore implements asynchronous tasks for creating per-customer and per-chatbot certificates and the requisite DNS TXT challenge records.

### Kubernetes Ingresses

Similarly, we also have to create an individual Ingress resource for each API domain.

### AWS Hosted Zones

Custom API domain names require a dedicated AWS Hosted Zone in order to generate the NS records that customers are responsible for adding to their DNS host.
