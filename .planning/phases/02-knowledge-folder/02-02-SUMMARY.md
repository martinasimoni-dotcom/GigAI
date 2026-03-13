---
phase: 02-knowledge-folder
plan: "02"
subsystem: knowledge-folder
tags: [knowledge-folder, demo-data, glossary, team-directory, rules, historical-patterns, harbor-view-tower]
dependency_graph:
  requires: [02-01]
  provides: [glossary-content, team-directory-content, rules-content, historical-patterns-content]
  affects: [Phase 3 seed script, Phase 4 retrieval, pgvector embedding corpus]
tech_stack:
  added: []
  patterns: [YAML rules schema, JSON event schema, Markdown chunked glossary]
key_files:
  created: []
  modified:
    - knowledge_folder/glossary/demo_project.md
    - knowledge_folder/team_directory/demo_project.json
    - knowledge_folder/rules/demo_project.yaml
    - knowledge_folder/historical_patterns/demo_project.json
decisions:
  - "5-section markdown glossary structure maps 1:1 to pgvector chunks (one ## section per chunk)"
  - "Historical patterns include 3 aluminum-to-wood accepted precedents (EVT-001/010/012) to support semantic retrieval of past change decisions"
  - "Rules use string-based condition fields (not eval-able code) — interpreted by LLM during enrichment, not executed programmatically"
metrics:
  duration: "3 min"
  completed_date: "2026-03-13"
  tasks_completed: 3
  files_modified: 4
---

# Phase 2 Plan 02: Knowledge Folder Content Files Summary

**One-liner:** Four Harbor View Tower knowledge files authored — glossary (5 sections/chunks), 7-member team directory, 18 YAML rules, and 12 historical change events including 3 aluminum-to-wood window precedents.

---

## What Was Built

All four knowledge folder content files populated with Harbor View Tower demo data, providing the full domain knowledge corpus for Wave 2 chunking, embedding, and pgvector storage.

### knowledge_folder/glossary/demo_project.md
- 5 `##` sections: Overview, Element Types, Materials, Locations, Abbreviations
- Materials section explicitly compares aluminum frames vs. wood frames with U-values, SHGC, lead times, costs
- Locations section calls out W-301 through W-312 as the 3rd floor demo scenario target units

### knowledge_folder/team_directory/demo_project.json
- 7 team members: Sarah Chen (PM), Mike Torres (Procurement), James Park (Architect), Lisa Wong (Structural Engineer), Carlos Rivera (Site Super), Jane Miller (Premium Wood Co. supplier), Robert Hayes (Owner Rep)
- All members have: name, role, email, phone, responsibilities[], area_of_authority
- Jane Miller is primary contact for aluminum-to-wood substitution quotes
- Robert Hayes triggers for any change order above $50,000

### knowledge_folder/rules/demo_project.yaml
- 18 rules under top-level `rules:` key
- Each rule has: rule_id, description, condition, action, stakeholders[], priority
- Key rules: RULE-003 ($50K escalation), RULE-005 (>10 units = 6-week lead), RULE-008 (>8 wood frame units = structural weight review), RULE-012 (vinyl rejected above floor 3)
- Compatible with `data.get("rules")` pattern in seed_knowledge_folder.py

### knowledge_folder/historical_patterns/demo_project.json
- 12 past material change events with all required fields
- 3 aluminum-to-wood window precedents (EVT-001, EVT-010, EVT-012) — all accepted
- EVT-001: 8-unit 5th floor penthouse substitution — primary precedent at sub-8 threshold
- EVT-012: 12-unit 4th floor — triggered structural review (RULE-008) and 6-week lead (RULE-005), direct precedent for 3rd floor demo scenario
- EVT-002: vinyl rejection precedent for semantic contrast during retrieval

---

## Self-Check: PASSED

All files verified present on disk. All three task commits (a19f7de, b8cbb19, 36ce70e) confirmed in git log.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write glossary and team directory | a19f7de | knowledge_folder/glossary/demo_project.md, knowledge_folder/team_directory/demo_project.json |
| 2 | Write rules file | b8cbb19 | knowledge_folder/rules/demo_project.yaml |
| 3 | Write historical patterns file | 36ce70e | knowledge_folder/historical_patterns/demo_project.json |

---

## Deviations from Plan

None — plan executed exactly as written. All content files match the exact specifications from the plan.

---

## Verification Results

All automated verification checks passed:
- Glossary: 5+ `##` sections, W-301 present, aluminum and wood terminology present
- Team: 7 members, all 6 required fields, Jane Miller present
- Rules: 18 rules, RULE-003 and RULE-005 present, $50,000 threshold present, all 6 required fields per rule
- Historical: 12 events, all 13 required fields per event, 3 aluminum-to-wood window precedents, EVT-001 is accepted aluminum-to-wood
