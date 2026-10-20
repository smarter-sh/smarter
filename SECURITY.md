# Security Policy

Smarter runs LLM applications that hold API keys, customer data and cloud
credentials, so we treat security reports as our highest priority. Thank you
for helping keep Smarter and its users safe.

## Reporting a Vulnerability

**Please do not report security vulnerabilities in public GitHub issues,
discussions or pull requests.**

Report them privately, in either of these ways:

1. **GitHub private vulnerability reporting (preferred).** Open the
   repository's [Security tab](https://github.com/smarter-sh/smarter/security)
   and choose **Report a vulnerability**. The report, and our discussion of it,
   stay private until an advisory is published.
2. **Email** [lpm0073@gmail.com](mailto:lpm0073@gmail.com), with
   `[smarter security]` in the subject.

Please include as much of the following as you can:

- the affected component, e.g. the REST API, the web console, a manifest kind,
  the Helm chart or the Docker image, and the affected versions,
- the impact: what an attacker can do, and with what access,
- steps to reproduce, a proof of concept, or the request and response,
- any known mitigation.

## What to Expect

| Stage                                       | Target                   |
| ------------------------------------------- | ------------------------ |
| Acknowledgement of your report              | 3 business days          |
| Initial assessment and severity (CVSS v3.1) | 7 days                   |
| Fix released, critical or high severity     | 30 days                  |
| Fix released, medium or low severity        | 90 days, or next release |
| Public disclosure                           | when the fix is released |

We will keep you informed of our progress, and may ask you for more
information. When the fix is released, we publish a
[GitHub Security Advisory](https://github.com/smarter-sh/smarter/security/advisories),
request a CVE when one is warranted, and credit you, unless you prefer to
remain anonymous.

We ask that you give us a reasonable time to release a fix before you
disclose the vulnerability publicly. If we cannot fix it within 90 days, we
will agree on a disclosure date with you.

## Supported Versions

Security fixes are released as patch releases of the latest minor version,
and are announced in the [changelog](https://github.com/smarter-sh/smarter/blob/main/changelogs/CHANGELOG.md)
and the advisory. The Docker image on
[Docker Hub](https://hub.docker.com/r/mcdaniel0073/smarter) and the
[Helm chart](https://artifacthub.io/packages/helm/project-smarter/smarter) are
published with every release.

| Version                       | Supported                                  |
| ----------------------------- | ------------------------------------------ |
| Latest minor release          | :white_check_mark:                         |
| Previous minor release        | Critical and high severity fixes, 3 months |
| Older releases                | :x:                                        |
| Pre-releases (alpha and beta) | :x:                                        |

## Scope

In scope:

- this repository: the Django platform, its REST API, the web console and its
  React apps, the manifest brokers, and the Celery tasks,
- the Docker image and the Helm chart that this repository publishes,
- the default configuration that they ship with.

Out of scope:

- vulnerabilities of third-party dependencies that Smarter does not expose;
  please report them upstream, and tell us if Smarter is affected,
- the behavior of LLM providers, and prompt injection that does no more than
  the prompt's author could do anyway; prompt injection that crosses an
  account boundary, leaks a secret, or calls a tool the user may not use is
  in scope,
- findings that need a compromised administrator account, physical access, or
  a misconfiguration that the documentation warns against,
- denial of service by volume, missing security headers without a
  demonstrated impact, and reports from automated scanners without a proof of
  concept,
- the hosted services at smarter.sh, other than through a vulnerability of
  this repository's code.

## Safe Harbor

We will not take legal action against, or ask law enforcement to investigate,
anyone who researches and reports a vulnerability in good faith under this
policy. Good faith means that you:

- test only against your own installation, or accounts you own,
- don't access, change or delete other users' data, and stop and report as
  soon as you encounter any,
- don't degrade the service for others, e.g. by load testing or spam,
- give us a reasonable time to fix the issue before you disclose it.

## Hardening Your Installation

Operators of a Smarter installation should also read the
[security documentation](https://docs.smarter.sh/smarter-platform/security.html).
In particular:

- set `SMARTER_SECRET_KEY` to a long, random value that every pod shares;
  outside of the local environment, Smarter refuses to start without one,
- keep the API rate limits, `SMARTER_THROTTLE_RATE_ANON` and
  `SMARTER_THROTTLE_RATE_USER`, enabled,
- keep secrets out of manifests and source control: store them as Smarter
  Secrets, or in your cloud's secret manager,
- upgrade to each patch release of your minor version promptly.
