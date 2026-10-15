Writing Secure Software for the Internet
========================================

**Why Smarter.** Security courses usually teach on deliberately vulnerable practice apps, which
show how attacks work but not how a real system defends itself. Smarter is a production system
that assumes a model will eventually try to do something it should not, and defends against it
with deterministic controls rather than instructions. That makes it a rich case study in both
classic web security and the new attacks on AI systems: prompt injection, jailbreaks, data
leakage, and server-side request forgery through tool calls. Every defense is in code that
students can read, test and try to break:

- **Guardrails on both sides of the model.** Built-in
  `guardrails <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__
  catch prompt injection by keyword and by LLM judge, jailbreaks and code injection on the way in,
  and leaked secrets, personal data and script injection on the way out, with deterministic
  `detectors <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/services/strategies/detectors.py>`__
  for credit cards, social security numbers, AWS keys, private keys and JWTs.
- **One hardened function for outbound requests.**
  `safe_http.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/safe_http.py>`__
  allows only https on port 443 to hosts whose every address is public, re-validates every
  redirect, bounds the response, and states in its own docstring the DNS rebinding window that
  remains. MCP connections get the same checks, and no stdio transport.
- **Credentials the model never sees.** Encrypted
  :doc:`Secrets </smarter-resources/smarter-secret>`, referred to by name; API Plugins whose keys
  are added by Smarter, not by the model; and a :doc:`Proxy </smarter-resources/smarter-proxy>`
  that keeps provider keys on the server.
- **Least privilege for tools.** SQL Plugins that run a fixed, parameterized query, and MCP
  clients that offer only the tools on an allow list.
- **A software supply chain for third-party code.** :doc:`Extensions
  </smarter-framework/extensibility>` run unsandboxed, with the platform's own access, so the
  `registry client
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/registry.py>`__
  verifies an Ed25519-signed index and every archive's sha256, the `archive
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/archive.py>`__
  is checked for zip bombs and path traversal before anything is imported, and administrators see
  each publisher's trust badge before they install.
- **Classic defenses too.** Hashed API keys, querysets filtered by owner, CSRF protection, CORS
  limited to each LLMClient's allowed origins, middleware that blocks scanners, a non-root
  container with read-only application files, and Calico network policies in
  `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__.
- **A secure development process.** ``bandit``, ``detect-private-key`` and
  ``detect-aws-credentials`` in the
  `pre-commit hooks <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__,
  Dependabot, image scanning, a `security policy
  <https://github.com/smarter-sh/smarter/blob/main/SECURITY.md>`__ for private reports, and
  :doc:`ADR 016 on security </adr/016-security>`.

The journal records every attack attempt and every intervention, so a red team exercise leaves
evidence that students can analyze afterwards.

**What the course covers.** The threat landscape, and the OWASP Top 10 and the OWASP Top 10 for LLM
Applications; injection and cross-site scripting, and how Django defends against them;
authentication, access control and broken object-level authorization; prompt injection, direct and
indirect, jailbreaks and data exfiltration; guardrails as deterministic controls, and measuring
their false positives; secrets at rest and in prompts; server-side request forgery, cloud metadata
addresses and DNS rebinding; infrastructure security, from containers to network policies; threat
modeling with data flow diagrams and STRIDE; secure development with static analysis, dependency
scanning and code review; and responsible disclosure and incident response.

**Look at.**

- `guardrail/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail>`__,
  its built-in guardrails, strategies and pipeline.
- `llmtool/plugin/safe_http.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/safe_http.py>`__
  and `mcpclient/connection.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/mcpclient/connection.py>`__.
- `lib/django/middleware/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/django/middleware>`__
  and `.pre-commit-config.yaml <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__.

Each course plan lists every file that it uses, defense by defense, under *Smarter in the Source
Code*.

**Read.** :doc:`/smarter-platform/security`, :doc:`/smarter-platform/security-faq`,
:doc:`/smarter-resources/smarter-guardrail`, :doc:`ADR 016 on security </adr/016-security>`.

**Exercises.**

- **Red team, blue team.** One team builds an LLMClient that guards a secret. The other tries to
  extract it with prompt injection. Then add guardrails, and try again. The journal records every
  attempt and every intervention.
- Map Smarter's defenses to the `OWASP Top 10 for LLM Applications
  <https://genai.owasp.org/llm-top-10/>`__ and the
  `OWASP Top 10 <https://owasp.org/www-project-top-ten/>`__, with the file that implements each,
  and find the gaps.
- Explain why an API plugin's credentials never appear in a prompt, and why a plugin may only
  fetch public https addresses. Then read ``safe_http.py`` as an attacker.
- Write a responsible disclosure report for a weakness that they find, and discuss how open source
  projects handle security reports.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <secure-software/bootcamp>
   Two-week online course: 6 hours <secure-software/two-week>
   Four-week online course: 12 hours <secure-software/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
