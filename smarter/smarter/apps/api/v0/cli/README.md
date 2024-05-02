# Smarter API command-line interface

This implements the REST API endpoints that back the Smarter command-line application (CLI), written in Go lang.
The Smarter CLI is available to download for Windows, macOS and Linux at these sites:

- [GitHub Releases](https://somewhere.org)
- [Homebrew](https://somewhere.org)
- [smarter.sh](https://somewhere.org)
- [snap](https://somewhere.org)

## Describe

calls: https://api.smarter.sh/v0/cli/describe/

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

calls https://api.smarter.sh/v0/cli/apply/


## Delete

Deletes a Smarter resource

```console
smarter delete plugin sales-demo
```

calls: https://api.smarter.sh/v0/cli/delete/

## Deploy

Deploys a Smarter resource

```console
smarter deploy []obj
```


calls: https://api.smarter.sh/v0/cli/deploy/

## Logs

prints log data for a resource

calls: https://api.smarter.sh/v0/cli/logs/

## Status

prints real-time status information about the state and availability of the Smarter platform

calls: https://api.smarter.sh/v0/cli/status/
