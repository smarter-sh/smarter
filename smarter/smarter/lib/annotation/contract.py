"""Pydantic models of annotation changes and selectors."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .validation import split_annotation_key

AnnotationAction = Literal["added", "changed", "removed"]
"""What happened to an annotation."""

AnnotationOperator = Literal["exists", "not_exists", "equals", "not_equals"]
"""How an :class:`AnnotationRequirement` tests a resource's annotation."""


class AnnotationChange(BaseModel):
    """One annotation of a resource that was added, changed or removed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(..., description="The annotation key, e.g. 'acme.com/crm-account-id'.")
    old_value: Optional[str] = Field(default=None, description="The value before the change, or None if it was added.")
    new_value: Optional[str] = Field(default=None, description="The value after the change, or None if it was removed.")

    @property
    def action(self) -> AnnotationAction:
        """Return ``added``, ``changed`` or ``removed``."""
        if self.old_value is None:
            return "added"
        if self.new_value is None:
            return "removed"
        return "changed"

    @property
    def prefix(self) -> Optional[str]:
        """Return the key's prefix, e.g. ``acme.com``, or ``None``."""
        return split_annotation_key(self.key)[0]


class AnnotationRequirement(BaseModel):
    """
    One requirement of an annotation selector, in the syntax of Kubernetes label selectors.

    ===========================  ==============================================
    Selector                     Matches resources whose annotation
    ===========================  ==============================================
    ``acme.com/crm-id``          ``acme.com/crm-id`` exists, with any value
    ``!acme.com/crm-id``         ``acme.com/crm-id`` doesn't exist
    ``acme.com/crm-id=A-10042``  ``acme.com/crm-id`` is ``A-10042``
    ``acme.com/crm-id!=A-10042`` ``acme.com/crm-id`` is missing, or isn't ``A-10042``
    ===========================  ==============================================
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(..., description="The annotation key.")
    operator: AnnotationOperator = Field(..., description="How the annotation is tested.")
    value: Optional[str] = Field(default=None, description="The value, for 'equals' and 'not_equals'.")

    def __str__(self) -> str:
        if self.operator == "exists":
            return self.key
        if self.operator == "not_exists":
            return "!" + self.key
        if self.operator == "equals":
            return f"{self.key}={self.value}"
        return f"{self.key}!={self.value}"


__all__ = ["AnnotationAction", "AnnotationChange", "AnnotationOperator", "AnnotationRequirement"]
