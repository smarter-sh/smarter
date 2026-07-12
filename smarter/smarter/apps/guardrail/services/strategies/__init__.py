"""Guardrail match-strategy implementations.

One concrete :class:`~smarter.apps.guardrail.services.strategies.base.BaseGuardrailStrategy`
subclass per :class:`smarter.apps.guardrail.models.MatchStrategy` value,
selected at runtime via
:func:`smarter.apps.guardrail.services.strategies.registry.get_strategy`.
Import from :mod:`smarter.apps.guardrail.services.strategies.registry`
rather than this package's submodules directly.
"""
