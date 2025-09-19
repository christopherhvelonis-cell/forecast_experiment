# Data Sheet - ${INDICATOR_ID}

**Source:**
**Unit:**
**Vintage Access:** (ALFRED/hosted snapshots).
**Revision Behavior:**
**Survey/Mode Changes:**
**Transform:** (see indicator_transform_spec.yml)
**Break Notes:**
**Provenance:** SHA256 for each vintage; logged in data/vintages.md.
**License/Terms:**

## Processing Steps
1. Ingest raw → UTC timestamp.
2. Annualize/harmonize.
3. Transform (z/logit/Box-Cox).
4. Impute (flagged) + outliers.
5. Break detection (PELT/Bai-Perron).
6. Export tidy series + annotations.
