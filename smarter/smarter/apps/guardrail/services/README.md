# Guardrail Services

The runtime of Smarter guardrails. The prompt pipeline uses this package to run
an LLMClient's guardrails on the user's message before it reaches the LLM, and
on the LLM's reply before it reaches the user.

The Django app around this package declares guardrails. Its manifest, broker,
`Guardrail` model and admin describe what a guardrail is. This package decides
what a guardrail _does_ to a prompt.

> **Experimental.** The Guardrail was designed and coded by Claude Code
> (Anthropic's Claude Opus 5.5), with Lawrence McDaniel as co-author. It is
> experimental, and will be documented.

## Usage

The only entry point is `GuardrailPipeline`. Everything else in this package
implements it.

```python
from smarter.apps.guardrail.services import GuardrailPipeline

pipeline = GuardrailPipeline.for_llmclient(llmclient, session_key=session_key)

pre = pipeline.run_pre({"messages": messages})
if pre.blocked:
    return pre.fallback_message  # never send a blocked message to the LLM
messages = pre.payload["messages"]  # possibly redacted

response = call_llm(messages)

post = pipeline.run_post(response)  # the chat completion, as a dict
reply = post.fallback_message if post.blocked else post.payload
```

In the platform, this is done by `handle_input_guardrails()` and
`handle_output_guardrails()` of `OpenAISmarterClient`, in
`lib/openai_compatible_chat_provider.py` of
`smarter/apps/provider/services/text_completion/`.
On a block, `handle_input_guardrails()` raises `GuardrailBlockedError`. The chat
handler catches it and answers with the guardrail's message, and a
`finish_reason` of `content_filter`, without calling the LLM.

`GuardrailPipeline(guardrails, llmclient=None, session_key=None,
record_events=True)` also accepts an explicit list of `Guardrail` rows. The
guardrail api's dry-run endpoint does this with `record_events=False`.

## How a prompt is evaluated

```text
GuardrailPipeline.run_pre / run_post
  │  guardrails_for(stage): the stage's active guardrails, by priority
  │
  └─ for each guardrail, in order:
       GuardrailEngine.evaluate()
         ├─ text_extraction.extract_segments()   which text to scan
         └─ get_strategy().evaluate()            does it trigger, and where?
       actions.apply_action()                    log, flag, redact, block...
       events.record_event()                     the GuardrailEvent audit row
       signals                                   guardrail_triggered, ...
       └─ a block stops the loop
```

- **Sequential.** Each guardrail sees the payload as the guardrails before it
  changed it, so a redaction at priority 10 hides the redacted text from a
  guardrail at priority 20.
- **Folded.** The pipeline's disposition is the most severe of its guardrails'
  dispositions: allowed < flagged < redacted < transformed < escalated <
  blocked. See `pipeline.fold()`.
- **Monitor mode.** A guardrail with `mode: monitor` is evaluated, and records
  a `monitored` event, but never changes or blocks the payload.
- **Failures.** A guardrail that fails to run, for example because its LLM
  provider is down, is recorded as an `error` event and skipped. With
  `failClosed: true`, it blocks instead. The engine catches every exception, so
  a broken guardrail never breaks a prompt.

## Modules

- **`pipeline.py`**: `GuardrailPipeline`, the entry point. It orders the
  guardrails, runs each one with the engine and its action, records events,
  sends signals, and returns a `PipelineResult`.
- **`engine.py`**: `GuardrailEngine.evaluate()` runs one guardrail's strategy on
  each text segment of a payload. It returns a `GuardrailOutcome` with a
  `GuardrailFinding` for each segment that triggered. It knows nothing of
  actions or events.
- **`text_extraction.py`**: finds the text to scan, and writes changes back.
  - Input: the **latest user message** only, not the system prompt or earlier
    turns.
  - Output: each choice's `content` and `refusal`.
  - Each segment has a path, e.g. `messages[3].content[0].text`, which
    `write_segment()` uses to write a redaction back to the right place.
- **`actions.py`**: `apply_action()` turns a finding into an `ActionOutcome`:
  the payload, possibly changed; the pipeline and event dispositions; and, for
  a block, the message. `replace_matches()` does redaction, including the
  `{label}` placeholder.
- **`events.py`**: `record_event()` writes a `GuardrailEvent`. `mask()` masks
  the excerpt of `pii` (last four characters kept) and `secrets` (length only),
  so the audit trail never stores what it protects.
- **`exceptions.py`**:
  - `GuardrailConfigError`, `GuardrailStrategyNotImplementedError` and
    `GuardrailProviderError`, which the engine records rather than raises.
  - `GuardrailBlockedError`, which the chat provider raises to stop a blocked
    prompt.
- **`strategies/`**: how a guardrail decides whether text triggers it. See
  [strategies/README.md](strategies/README.md).

The services pass around data types that are Pydantic models, in
`smarter/apps/provider/services/text_completion/contracts.py`:
`GuardrailStage`, `TextSegment`, `GuardrailMatch`, `GuardrailFinding`,
`GuardrailOutcome`, `PipelineDisposition` and `PipelineResult`.

## Extending

- **A new action:** add it to `SAMGuardrailAction` in `manifest/enum.py`, and to
  `GuardrailAction` in `models/guardrail.py`, with a migration. Then add a
  `_handle_<action>` function in `actions.py`.
- **A new strategy:** see [strategies/README.md](strategies/README.md).

## Testing

The tests are in `smarter/apps/guardrail/tests/`: `test_pipeline`,
`test_actions`, `test_events`, `test_text_extraction` and
`test_prompt_integration`. For guardrails that call an LLM provider, use
`fake_client()` from `tests/base_classes.py`, so the tests make no network
calls.

```bash
python manage.py test smarter.apps.guardrail
```
