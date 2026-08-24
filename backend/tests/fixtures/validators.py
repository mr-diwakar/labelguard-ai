from app.compliance.registry import ValidatorRegistry
from app.compliance.validators.required import RequiredDeclarationValidator


class BrokenValidator:
    def validate(self, rule, declarations, context):
        raise RuntimeError("unexpected validator failure")


def broken_required_registry() -> ValidatorRegistry:
    registry = ValidatorRegistry()
    registry.register("REQUIRED_DECLARATION", BrokenValidator())
    return registry


def required_only_registry() -> ValidatorRegistry:
    registry = ValidatorRegistry()
    registry.register("REQUIRED_DECLARATION", RequiredDeclarationValidator())
    return registry
