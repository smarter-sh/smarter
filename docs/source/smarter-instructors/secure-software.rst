Writing Secure Software for the Internet
========================================

**Why Smarter.** Smarter assumes that a model will eventually try to do something it should not,
and defends against it with deterministic controls rather than instructions. That makes it a rich
case study in both classic web security and the new attacks on AI systems: prompt injection,
jailbreaks, data leakage, and server-side request forgery through tool calls.

**Look at.** The guardrails in ``smarter/smarter/apps/guardrail/data/guardrails/``, the hardened
outbound HTTP code in ``smarter/smarter/apps/plugin/plugin/safe_http.py``, encrypted :doc:`Secrets </smarter-resources/smarter-secret>`,
and the ``bandit``, ``detect-private-key`` and ``detect-aws-credentials`` hooks in
``.pre-commit-config.yaml``.

**Read.** :doc:`/smarter-platform/security`, :doc:`/smarter-platform/security-faq`,
:doc:`/smarter-resources/smarter-guardrail`, :doc:`ADR 016 on security </adr/016-security>`.

**Exercises.**

- **Red team, blue team.** One team builds an LLMClient that guards a secret. The other tries to
  extract it with prompt injection. Then add guardrails, and try again. The journal records every
  attempt and every intervention.
- Map Smarter's defenses to the `OWASP Top 10 for LLM Applications
  <https://genai.owasp.org/llm-top-10/>`__ and the `OWASP Top 10 <https://owasp.org/www-project-top-ten/>`__.
- Explain why an API plugin's credentials never appear in a prompt, and why a plugin may only
  fetch public https addresses.
- Write a responsible disclosure report for a weakness that they find, and discuss how open source
  projects handle security reports.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
