# Smarter API command-line interface

This implements the REST API endpoints that back the Smarter command-line application (CLI), written in Go lang.
The Smarter CLI is available to download for Windows, macOS and Linux at these sites:

- [somewhere](https://somewhere.org)
- [somewhere](https://somewhere.org)
- [somewhere](https://somewhere.org)

## Get

```console
smarter get plugins
smarter get chatbots
smarter get chat
```

Returns json or yaml

## Apply

Applies a Smarter manifest.

```console
smarter apply -f 'desktop/plugins/sales-demo.yaml' --json
```

## Delete

Deletes a Smarter resource

```console
smarter delete plugin sales-demo
```
