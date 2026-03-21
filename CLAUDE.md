<!-- GSD:project-start source:PROJECT.md -->
## Project

**PROJECT.md — GigAI**

GigAI is an AI-powered construction project management platform that automates material change coordination, project/employee management, schedule predictions, and cross-stakeholder communication for construction PMs. It reduces 4+ hours of manual PM coordination to under 12 minutes per change.

**Core Value:** Eliminate manual PM coordination burden by automating capture, enrichment, proposal generation, action execution, and communication — turning PMs from paperwork processors into decision-makers.

### Constraints

- **Tech stack**: Must integrate with existing Python/FastAPI backend and React frontend — no new frameworks
- **Predictions**: Must use academically-grounded prediction models (earned value, Monte Carlo, Bayesian) — not heuristics
- **Quality**: Production-ready code — reliable, accurate, detailed
- **Design**: Maintain Apple macOS dark mode aesthetic consistency
- **LLMs**: Claude Sonnet 4 for complex analysis, Haiku 4.5 for classification/extraction
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
