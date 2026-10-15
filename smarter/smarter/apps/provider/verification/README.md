# Provider Verification

Self-onboarding readiness tests for Provider and Provider Models.
These are run when new records for either are created / updated, and they're also run periodically via Celery Beat.

A Provider Model is activated when it passes every check its `supports_*` fields call for, and deactivated when it
fails one. An error that is about the account or the provider rather than the model (an invalid api key, an account
without credit, a rate limit, an outage or a network error) is inconclusive: the run stops and the model stays as it
was. `initialize_providers` creates only models that can chat, so it skips the Gemini models whose
`supportedGenerationMethods` lack `generateContent` (embedding, video, question answering and Live models).
It creates new providers verified and active, and new models active, and their verification decides whether they stay
so. Running it again, as every deploy does, leaves an existing provider's `status`, `is_active`, `is_verified`,
`is_deprecated`, `is_flagged` and `is_suspended`, and an existing model's `is_active`, as verification or an admin last
set them.
