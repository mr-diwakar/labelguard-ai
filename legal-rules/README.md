# Legal rule source data

Structured metadata for the LabelGuard legal-rule store.

This folder does **not** replace the official government text. It records internal identifiers, source references and applicability notes so the compliance engine can load versioned rows later.

## Authoritative sources

1. Department of Consumer Affairs — Legal Metrology: https://consumeraffairs.gov.in/pages/legal-metrology-act
2. Official consolidated publication of the Packaged Commodities Rules, 2011 with amendments (DoCA): https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/Book_on_Legal_Metrology_Packaged_Commodities_Rules%2C2011_with_all_amendments_whatsnews.pdf
3. India Code text of the 2011 Rules (G.S.R. 202(E), 7 March 2011): used to verify the Phase 6 prototype clauses.

Do not treat blogs, commercial sites or unofficial summaries as overriding these sources.

## What is stored

`2011/rules.json` holds a **small prototype set**. Each row is a LabelGuard `rule_code`, not a government rule number.

`VERIFIED` means the clause was read from the official 2011 India Code text. `UNVERIFIED` / `DRAFT` rows must not be used as production-authoritative law.

## Adding an amendment

1. Verify the amendment against the official DoCA consolidated publication.
2. Do not overwrite the existing JSON object.
3. Add a new object with the same `rule_code`, a new `source_version`, and a new `effective_from`.
4. Set the previous object's `effective_to` to the day before the amendment takes effect.
5. Re-run `python -m seeds.legal_rules` from `backend/`.
