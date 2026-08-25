"""
Scan pipeline (Phases 16-19).

Integration layers that sit ABOVE both the declaration-extraction layer (Phase 15,
``app.extraction``) and the Legal Metrology engine (``app.compliance``), adapting DOWN
to their stable contracts. These modules orchestrate; they never re-implement a legal
rule, an extractor, or a verdict vocabulary.

Public API grows one milestone at a time:
    * Phase 16 -- ``assess_extraction`` / ``declarations_for_engine`` (legal.py)
    * Phase 17 -- ``verify`` / ``verify_one`` / ``measured_value_from_text`` (verification.py)
    * Phase 18 -- ``build_guidance`` (guidance.py)
    * Phase 19 -- ``run_scan`` (orchestrator.py)
"""

from app.pipeline.guidance import build_guidance
from app.pipeline.legal import assess_extraction, declarations_for_engine
from app.pipeline.orchestrator import run_scan
from app.pipeline.verification import measured_value_from_text, verify, verify_one

__all__ = [
    "assess_extraction",
    "declarations_for_engine",
    "verify",
    "verify_one",
    "measured_value_from_text",
    "build_guidance",
    "run_scan",
]
