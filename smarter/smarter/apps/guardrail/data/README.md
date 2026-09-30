# Built-in Guardrails

`guardrails/` contains the built-in Guardrail manifests, which cover the most common use
cases. `manage.py add_builtin_guardrails` applies them for the Smarter admin user, so that
every account's LLMClients may list them in their `spec.guardrails`. They are also examples
to copy and adapt, e.g. the scope of `off_topic_input`.
