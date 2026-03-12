# CLAUDE.md — GigAI Implementation Guide

## What Is GigAI

GigAI is an event-driven coordination automation system for construction project managers. It monitors project activity (meeting transcripts, emails, ACC updates, calendar changes), processes events through an AI pipeline, generates coordination proposals, and executes approved actions via external APIs.

Demo scenario: Window material substitution — Aluminum -> Wood, 3rd Floor, 12 Units.

## Architecture Overview

INPUT -> SYSTEM -> OUTPUT

- INPUT: webhooks/connectors publish events to bus
- SYSTEM: normalization, routing, enrichment, domain processing, decision intelligence
- OUTPUT: proposal formatting, PM approval, API execution, notifications, feedback learning

## File Structure

```text
material-change-coordinator/
├── CLAUDE.md
├── README.md
├── PRD.md
├── requirements.txt
├── .env.example
├── pyproject.toml
├── src/
│   ├── main.py
│   ├── input/
│   │   ├── webhooks/
│   │   │   ├── fireflies.py
│   │   │   └── acc.py
│   │   └── connectors/
│   │       ├── gmail.py
│   │       └── calendar.py
│   ├── system/
│   │   ├── data_processing/
│   │   │   ├── normalizer.py
│   │   │   ├── scope_filter.py
│   │   │   └── router.py
│   │   ├── context/
│   │   │   ├── enrichment.py
│   │   │   └── historical.py
│   │   ├── domain_processing/
│   │   │   ├── processor.py
│   │   │   ├── time_analysis.py
│   │   │   ├── policy_engine.py
│   │   │   └── signal_generator.py
│   │   └── decision_intelligence/
│   │       ├── proposal_generator.py
│   │       └── confidence_scorer.py
│   ├── output/
│   │   ├── proposal_builder/builder.py
│   │   ├── action_gateway/
│   │   │   ├── gateway.py
│   │   │   ├── acc_executor.py
│   │   │   ├── gmail_executor.py
│   │   │   ├── calendar_executor.py
│   │   │   └── document_executor.py
│   │   ├── notifications/
│   │   │   ├── dashboard_notifier.py
│   │   │   ├── acc_notifier.py
│   │   │   └── email_notifier.py
│   │   └── feedback/feedback_loop.py
│   ├── shared/
│   │   ├── models/{events.py,proposals.py,config.py}
│   │   ├── llm/{claude.py,voyage.py}
│   │   └── db/{postgres.py,vector_store.py}
│   └── api/
│       ├── routes.py
│       └── middleware.py
├── knowledge_folder/
│   ├── glossary/demo_project.md
│   ├── team_directory/demo_project.json
│   ├── rules/demo_project.yaml
│   └── historical_patterns/demo_project.json
├── config/
│   ├── settings.py
│   ├── event_types/{material_change.yaml,schedule_update.yaml,rfi_request.yaml}
│   └── prompts/{normalization.txt,routing.txt,proposal.txt}
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
│   ├── seed_knowledge_folder.py
│   ├── seed_demo_data.py
│   ├── run_demo.py
│   └── test_retrieval_quality.py
├── infra/
│   ├── sql/{001_create_tables.sql,002_create_indexes.sql}
│   ├── pubsub/setup.sh
│   └── cloud_run/{Dockerfile,cloudbuild.yaml}
└── dashboard/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
```

## Constraints

- Python 3.11 + FastAPI.
- Pydantic v2 for validation.
- Anthropic + Voyage clients in `src/shared/llm/`.
- PostgreSQL + pgvector in `src/shared/db/`.
- Human-in-the-loop approval before action execution.
