"""Validator contract. Implementations must not import FastAPI, SQLAlchemy, or OCR."""

from collections.abc import Sequence
from typing import Protocol

from app.schemas.declaration import Declaration
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.validation import ValidationContext, ValidationResult


class Validator(Protocol):
    def validate(
        self,
        rule: LegalRuleRecord,
        declarations: Sequence[Declaration],
        context: ValidationContext,
    ) -> ValidationResult: ...
