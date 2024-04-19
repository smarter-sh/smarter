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

The Smarter application stack needs to provide consistent behavior for either of three different styles of domain name

- Default ChatBot domain names: [subdomain].[####-####-####].[environment].smarter.sh/chatbot/
- Customer's custom domain names: [subdomain].example.com/chatbot/
- The Smarter API: /api/v0/chatbots/[int]/[ChatBot.name]

Secondarily, it also needs to gracefully adapt to alternatives like `localhost`, `127.0.0.1` and conjured up names used in unit tests.

## URL Parsing and Routing

In light of the multiple naming schemes, mapping hosts and urls to a ChatBot is not trivial.

and provide reliable and performant functions for URL parsing as well as instantiating Account, ChatBot and User objects related to the domain. Also be aware that the singleton `smarter.common.conf.settings` implements `settings.customer_api_domain`.

- `smarter.apps.chatbot.models.ChatBotHelper`: Maps a url to its ChatBot, Plugin list, Account and User objects.
- `smarter.lib.django.validators.SmarterValidator`: Low-level url parsing features.
- `smarter.common.conf.settings`: A singleton that provides settings values for the environment and base customer API domains.

## Default Domain

The default domain for each ChatBot is accessible regardless of whether the customer has also implemented a custom domain.

example: https://example.3141-5926-5359.api.smarter.sh/chatbot/

where

- `/chatbot/` is a URL endpoint defined in smarter/urls.py and resolves to a Django View that invoke Chat with a List of Smarter Plugin objects.

- `example' == ChatBot.name`
- `3141-5926-5359 == ChatBot.account.account_number`
- `api.smarter.sh == smarter_settings.customer_api_domain`

## Custom Domain

Customers can configure a custom domain for their account, mapping individual chatbots to DNS subdomain records aliased to the master Kubernetes ingress controller for the platform. Smarter provides `manage.py` admin commands for managing the complete lifecycle of customer custom domain recourses.

example: https://api.smarter.querium.com/chatbot/
where

- `api.smarter.querium.com == chatbot.custom_domain`: A ChatBotCustomDomain object
- `ChatBotCustomDomain.is_verified == True`: An asynchronous task verifies the domain NS records.

The ChatBot instance hostname is determined by the following logic: `chatbot.hostname == ChatBot.custom_domain` once the domain is verified and the chatbot is deployed.

## Application Configuration Considerations

There are multiple Django configuration implications due the additional subdomains prefixed to default customer domains, as well as the fact that custom domains need to be treated as if they were in fact the platform root domain, `smarter.sh`. This domain naming styles requires customizations to url routing within Django, as well as to `ALLOWED_HOSTS`, CORS, CSRF, ssl-certificates, and Kubernetes Ingresses.

### ALLOWED_HOSTS

For Django to accept http requests from any domain, it must be included in Django's `ALLOWED_HOSTS` settings which is then managed by Django middleware that we've subclassed as `smarter.apps.chatbot.middleware.security.SecurityMiddleware` in order to append customer API domains to `ALLOWED_HOSTS` at run time.

### CORS

We subclassed the standard `corsheaders` as `smarter.apps.chatbot.middleware.cors.CorsMiddleware` in order to performantly append customer API domains to its `CORS_ALLOWED_ORIGINS` at run time..

### Cross-Site Request Forgery

We subclassed Django's csrf library as `smarter.apps.chatbot.middleware.csrf.CsrfViewMiddleware` in order to performantly append customer domains to `CSRF_TRUSTED_ORIGINS` at run time.

### TLS/SSL Certificates

The certificates issued and managed by `cert-manager` for each environment only support one subdomain, implemented as a wildcard, `*.[environment].smarter.sh` and thus, customer API domains fall outside of this scheme. Smarter therefore implements asynchronous tasks for creating per-customer and per-chatbot certificates and DNS TXT challenge records.

### Kubernetes Ingresses

Similarly, we also have to create individual Ingress resources.

### AWS Hosted Zones

Custom API domains require a dedicated AWS Hosted Zone in order to generate the NS records that customers are responsible for adding to their DNS host.
