"""Maps validation_type to a validator. Callers supply the rule; nothing is loaded here."""

from app.compliance.validators.consumer_care import ConsumerCareValidator
from app.compliance.validators.date_declaration import DateDeclarationValidator
from app.compliance.validators.mrp import MRPValidator
from app.compliance.validators.net_quantity import NetQuantityValidator
from app.compliance.validators.protocol import Validator
from app.compliance.validators.required import RequiredDeclarationValidator
from app.core.enums import ValidationType


class ValidatorRegistry:
    def __init__(self) -> None:
        self._validators: dict[str, Validator] = {}

    def register(self, validation_type: ValidationType | str, validator: Validator) -> None:
        self._validators[str(validation_type)] = validator

    def get(self, validation_type: ValidationType | str) -> Validator | None:
        return self._validators.get(str(validation_type))

    def resolve(self, validation_type: ValidationType | str) -> Validator:
        validator = self.get(validation_type)
        if validator is None:
            raise KeyError(f"No validator is registered for {validation_type}.")
        return validator


def build_default_registry() -> ValidatorRegistry:
    registry = ValidatorRegistry()
    registry.register(ValidationType.REQUIRED_DECLARATION, RequiredDeclarationValidator())
    registry.register(ValidationType.MRP_VALIDATION, MRPValidator())
    registry.register(ValidationType.NET_QUANTITY_VALIDATION, NetQuantityValidator())
    registry.register(ValidationType.DATE_VALIDATION, DateDeclarationValidator())
    registry.register(ValidationType.CONSUMER_CARE_VALIDATION, ConsumerCareValidator())
    return registry
