# Smarter for IT Leadership

**Audience:** IT leadership (VP and above) at large organizations. The deck
speaks to four roles in turn: the CIO, the head of custom programming, the head
of infrastructure, and the head of technical support. They want the big
picture, in technical terms.

**Presenter:** Lawrence McDaniel, November 2026. 16 slides, about 30 minutes.

**The argument:** bottom-up AI adoption has produced AI sprawl: provider keys
everywhere, a separate stack per team, no cost attribution and no audit trail.
Smarter is a self-hosted control plane in which every AI capability, from a
model key to a guardrail, is a declared resource with an owner, a budget and
an audit trail. The deck covers:

- the architecture, the four-layer resource model and an example manifest
- for the CIO: vendor control, cost control, no lock-in, a talent pipeline, AGPL licensing
- for custom programming: less routine code to own, and standard integration points
- for infrastructure: Docker Compose to Helm to Terraform, the security architecture, and commercial and self-hosted models
- for technical support: traceability from account to prompt record, cost records, runtime diagnostics
- maturity and the gaps to plan for (enterprise SSO, AWS-only provisioning, community support, perimeter controls), and a 90-day pilot

The manifest on slide 6 is abridged, and its assistant and plugin names are illustrative.

- [smarter-for-it-leadership.json](smarter-for-it-leadership.json): the text and speaker notes of every slide
- [source/](source/): the deck itself

See [../README.md](../README.md) for the file formats.
