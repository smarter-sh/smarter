# Guardrail Strategies

A strategy decides whether a piece of text triggers a guardrail, with what
confidence and, if it can, where in the text. That is all it does.
`../actions.py` decides what happens next (redact, block, flag and so on), and
`../pipeline.py` decides the order in which guardrails run. See
[../README.md](../README.md).

> **Experimental.** The Guardrail was designed and coded by Claude Code
> (Anthropic's Claude Opus 5.5), with Lawrence McDaniel as co-author. It is
> experimental, and will be documented.

## Usage

Strategies are stateless singletons, looked up by the value of a guardrail's
`strategy`:

```python
from smarter.apps.guardrail.services.strategies.base import StrategyContext
from smarter.apps.guardrail.services.strategies.registry import get_strategy

match = get_strategy(guardrail.strategy).evaluate(
    segment=segment,  # a TextSegment: the text, and its path in the payload
    guardrail=guardrail,  # the Guardrail row; see guardrail.settings
    context=StrategyContext(stage=stage),
)
match.triggered, match.confidence, match.matches, match.rationale
```

Normally you don't call a strategy yourself. `GuardrailEngine` calls one for
each text segment.

## The strategies

Three strategies run locally, in microseconds, and **locate** their matches.
They return the character span of each match as a `GuardrailMatch`, which the
`redact` and `transform` actions need.

- **`regex`** (`regex_strategy.py`)
  - Fields: `pattern`, and `flags`. The flags are any of `IGNORECASE` (the
    default), `MULTILINE` and `DOTALL`.
  - Runs `finditer` over the whole segment, up to `MAX_MATCHES` matches.
    `compile_pattern()` caches the compiled patterns.
- **`keyword`** (`keyword_strategy.py`)
  - Fields: `keywords`, `caseSensitive` (default false) and `wholeWord`
    (default true).
  - Compiles the keywords into one pattern. Whitespace inside a phrase matches
    any whitespace, so a phrase split across lines still matches.
- **`detector`** (`detector_strategy.py`, with the detectors in `detectors.py`)
  - Fields: `detectors`, any of `credit_card` (Luhn-validated), `us_ssn`,
    `email`, `phone_number`, `ip_address` (validated), `iban`
    (mod-97-validated), `aws_access_key`, `private_key`, `api_key`, `jwt` and
    `password_assignment`.
  - The detectors favor precision over recall, so a 16 digit order number is
    not taken for a card number. `detect()` merges overlapping matches and
    keeps the longest.

Three strategies call an LLM provider, and are **scored**. They trigger when
their score reaches the guardrail's `threshold`, whose default comes from
`BaseGuardrailStrategy.threshold()`. They do not locate, so the manifest
rejects `redact` and `transform` with them. They are slower and cost money, so
give them a higher `priority` number than the local strategies, which makes
them run later.

- **`semantic`** (`semantic_strategy.py`)
  - Fields: `referenceTexts`, `threshold`, `model` and `provider`.
  - Takes the cosine similarity between the segment's embedding and each
    reference text's embedding. The Django cache holds the reference
    embeddings, keyed by the model and the sha256 of the text, so each prompt
    embeds only the segment.
- **`moderation`** (`moderation_strategy.py`)
  - Fields: `categories`, `threshold`, `model` and `provider`.
  - Uses the provider's moderation model, for example `omni-moderation-latest`.
    Triggers when a listed category's score reaches the threshold, or any
    category's if none are listed, or when the model flags one.
- **`llm_judge`** (`llm_judge_strategy.py`)
  - Fields: `judgePrompt`, `threshold`, `model` and `provider`.
  - Sends `judgePrompt` with `{text}` replaced by the segment. The judge must
    reply with a JSON verdict, `{"triggered", "confidence", "rationale"}`,
    which `clients.parse_verdict()` parses. A system message tells the judge
    that the text is untrusted data whose instructions it must not follow.

## LLM provider clients

`clients.py` keeps the scored strategies independent of any one provider.

- `GuardrailClient` is the protocol they call: `embed()`, `moderate()` and
  `judge()`.
- `OpenAIGuardrailClient` implements it with the OpenAI SDK, for any
  OpenAI-compatible Smarter `Provider`. Its timeout is 15 seconds, and it
  retries once. It raises SDK errors as `GuardrailProviderError`.
- `default_client_for(guardrail)` returns a client for the Provider named in
  the guardrail's `provider` field (`openai` by default), with that Provider's
  API key. The guardrail's owner must be able to read the Provider. Clients are
  cached, and replaced when the Provider changes.
- `get_client(guardrail)` is what strategies call. `configure_clients(factory)`
  replaces the factory, and `configure_clients(None)` restores the default.
  Tests do this through `fake_client()` in `tests/base_classes.py`.

## Modules

- **`base.py`**: the abstract `BaseGuardrailStrategy.evaluate()`.
  `StrategyContext` holds the stage and the request id. `StrategyMatch` holds
  triggered, confidence, matches and rationale.
- **`registry.py`**: `get_strategy(name)`, the map from `GuardrailStrategy`
  values to strategy instances. It re-exports `configure_clients` and
  `get_client`.
- **`clients.py`**: the LLM provider clients, described above.
- **`detectors.py`**: the built-in detectors, each a regex plus a validator
  where the data has a checksum, and `detect()`.
- **`*_strategy.py`**: one strategy each, described above.

## Adding a strategy

1. Add the value to `SAMGuardrailStrategy` in `manifest/enum.py`, and to its
   `scored()` or `locating()` if it applies. Add it to `GuardrailStrategy` in
   `models/guardrail.py`, with a migration.
2. Add its manifest fields to `SAMGuardrailSpecConfig` in
   `manifest/models/guardrail/spec.py`, with validation in
   `validate_strategy_fields()`. Add the fields to `STRATEGY_FIELDS` in
   `manifest/brokers/guardrail.py`, so they are stored in `Guardrail.config`.
3. Write `<name>_strategy.py`, with a subclass of `BaseGuardrailStrategy`.
   Read its settings from `guardrail.settings`, and raise
   `GuardrailConfigError` for a bad configuration. If it calls a provider, call
   `get_client(guardrail)`, adding a method to `GuardrailClient` if needed.
4. Register it in `_STRATEGIES` in `registry.py`.
5. Test it in `tests/test_strategies.py`, using the fake client for provider
   calls.
