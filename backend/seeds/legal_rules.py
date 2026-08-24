"""Load prototype legal rules from legal-rules/2011/rules.json without duplicating versions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.compliance.repository import LegalRuleRepository
from app.core.logging_config import configure_logging, get_logger
from app.database.connection import dispose_engine, get_session_factory
from app.schemas.legal_rule import LegalRuleCreate

logger = get_logger("seed")

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = REPO_ROOT / "legal-rules" / "2011" / "rules.json"


def load_rule_payloads(path: Path = RULES_PATH) -> list[LegalRuleCreate]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return [LegalRuleCreate.model_validate(item) for item in document["rules"]]


def seed_legal_rules(session: Session, path: Path = RULES_PATH) -> dict[str, int]:
    repository = LegalRuleRepository(session)
    created = 0
    updated = 0

    for payload in load_rule_payloads(path):
        existing = repository._version_query(
            payload.rule_code,
            payload.source_version,
            payload.effective_from,
        ).scalar_one_or_none()
        repository.upsert_rule(payload)
        if existing is None:
            created += 1
        else:
            updated += 1

    session.commit()
    logger.info("stage=seed created=%s updated=%s path=%s", created, updated, path)
    return {"created": created, "updated": updated, "total": created + updated}


def main() -> None:
    from app.core.config import get_settings

    configure_logging(get_settings())
    session = get_session_factory()()
    try:
        result = seed_legal_rules(session)
        print(f"Seed complete created={result['created']} updated={result['updated']} total={result['total']}")
    finally:
        session.close()
        dispose_engine()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
