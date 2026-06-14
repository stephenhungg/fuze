# sample data

synthetic nonprofit source files for ingestion and demo testing.

this folder is meant to look like what a small nonprofit might connect from
microsoft 365, google drive, local csv exports, and restricted case folders.
the data is fake, deterministic, and safe to commit.

## corpus shape

```text
sample_data/harbor_light/
  manifest.json
  grant_requirements.txt
  program_metrics.csv
  volunteers.csv
  board_minutes.txt
  finance_export_may.csv
  staff_directory.csv
  story_consent_tracker.csv
  case_notes.txt
  approved_story_bank.md
  donor_crm_export.csv
  compliance_calendar.md
  board_risk_register.md
  sharepoint_delta_sample.json
```

## intended ingestion behavior

the index agent should:

1. read `manifest.json`
2. parse each source file
3. partition docs into sections/rows/records
4. attach connector, source type, sensitivity, allowed roles, and citations
5. classify pii and external-output rules
6. upsert chunks to qdrant
7. update graph entities and edges
8. emit index-agent events to `/events/stream`

## demo note

the current app still uses deterministic seeded data in `api/db.py`, but this
corpus mirrors those records so the next ingestion slice can replace hand-seeded
chunks with file-derived chunks.
