# GigAI Meeting Intelligence System

## Overview

The **Meeting Intelligence System** is an AI-powered module that listens to architectural meetings, automatically detects design changes, and creates actionable BIM coordination tasks. It integrates seamlessly with the existing GigAI orchestrator to turn verbal discussions into marked-up Revit models, documented decisions, and assigned tasks.

## System Flow

```
Meeting Transcript
    ↓
Architectural NLP Parser
    ├─ Extract spaces (rooms, units, facades)
    ├─ Detect actions (resize, move, modify, add, remove)
    ├─ Extract change descriptions
    └─ Identify affected elements
    ↓
Meeting Event Processor
    ├─ Fetch from Fireflies API
    ├─ Parse full transcript
    └─ Generate meeting context
    ↓
BIM Element Identifier
    ├─ Map spaces to Revit rooms
    ├─ Find affected elements
    └─ Extract properties
    ↓
Decision Pipeline Integration
    ├─ Design Change Agent analyzes changes
    ├─ Generate proposals and alternatives
    ├─ Assess risks and constraints
    └─ Build decision packages
    ↓
Decision & Authority Check (via GigAI orchestrator)
    ├─ Apply policy and security rules
    ├─ Check confidence and risk levels
    ├─ Route to approval or auto-execute
    └─ Return authority decision (auto/manual)
    ↓
Revision Executor
    ├─ Create revision clouds in Revit
    ├─ Attach comments with change details
    ├─ Update BIM360 with references
    └─ Log all actions to database
    ↓
Task Assignment & Notifications
    ├─ Assign tasks to responsible architects
    ├─ Create calendar events
    ├─ Send email notifications
    └─ Generate meeting minutes
    ↓
GigAI Dashboard
    └─ Display all updates and tracking
```

## Modules

### 1. **Architectural Parser** (`architectural_parser.py`)
Extracts design changes from meeting transcripts using pattern matching and NLP.

**Key Features:**
- Space identification (rooms, units, facades)
- Action detection (resize, move, modify, add, remove, change_material)
- Property extraction (dimensions, materials, colors)
- Confidence scoring

**Usage:**
```python
from gigai.meeting_intelligence import ArchitecturalNLPParser

parser = ArchitecturalNLPParser()
changes = parser.parse_transcript(transcript_text, project_id, meeting_id)

for change in changes:
    print(f"{change.space}: {change.action} {change.element_type}")
```

### 2. **Meeting Event Processor** (`meeting_processor.py`)
Orchestrates the complete meeting intelligence workflow.

**Key Features:**
- Fetches transcripts from Firefiles API
- Extracts architectural changes
- Identifies BIM elements
- Generates meeting context
- Emits events to pipeline

**Usage:**
```python
from gigai.meeting_intelligence import MeetingEventProcessor

processor = MeetingEventProcessor()
result = await processor.process_meeting_from_fireflies(
    fireflies_meeting_id="ff_abc123",
    project_id="proj_tower_a",
    project_name="Residential Tower A"
)

print(f"Changes detected: {len(result.architectural_changes)}")
```

### 3. **BIM Element Identifier** (`bim_identifier.py`)
Maps architectural changes to actual BIM elements in Revit.

**Key Features:**
- Space/room lookup with fuzzy matching
- Element finding by space and type
- Property extraction
- Mock BIM data for MVP, ready for real Revit API

**Usage:**
```python
from gigai.meeting_intelligence import BIMElementIdentifier

identifier = BIMElementIdentifier()
elements = identifier.find_elements_for_change(architectural_change)

for element in elements:
    print(f"Element {element.element_id}: {element.element_type}")
```

### 4. **Revit REST Client** (`revit_rest_client.py`)
Communication layer for Revit operations.

**Key Features:**
- Query spaces and elements
- Create revision clouds
- Attach comments
- Update parameters
- Mock server for testing

**Usage:**
```python
from gigai.revit import RevitRESTClient

client = RevitRESTClient()
spaces = await client.get_all_spaces()
elements = await client.get_elements_in_space("room_001")

# Create revision
cloud_id = await client.create_revision_cloud(revision_marker)
```

### 5. **Revision Executor** (`revision_executor.py`)
Coordinates revision placement in Revit when decisions are approved.

**Key Features:**
- Receives approved design changes
- Creates revision clouds in Revit
- Attaches detailed comments
- Writes back to BIM360
- Full audit logging

**Usage:**
```python
from gigai.meeting_intelligence import RevisionExecutor

executor = RevisionExecutor()
revision = await executor.execute_revision(
    change=architectural_change,
    decision_id="d_456",
    project_id="proj_tower_a",
    meeting_id="meet_001",
    requested_by="Architect_A"
)
```

### 6. **Meeting Decision Agent** (`meeting_decision_agent.py`)
Integrates meeting intelligence with GigAI decision pipeline.

**Key Features:**
- Analyzes architectural changes
- Generates proposals and alternatives
- Assesses risks and constraints
- Builds decision packages
- Integrates with orchestrator

**Usage:**
```python
from gigai.meeting_intelligence import DesignChangeAgent

agent = DesignChangeAgent()
agent_output = agent.analyze_changes(meeting_result)
decisions = agent.build_decision_package(
    meeting_result,
    agent_output,
    meeting_id
)
```

## Configuration Files

### Architectural Vocabulary (`config/architectural_vocabulary.json`)
Defines architectural terminology, aliases, and building elements.

```json
{
  "actions": [
    {"action": "resize", "aliases": ["increase", "expand", "shrink", ...]},
    {"action": "move", "aliases": ["shift", "relocate", ...]},
    ...
  ],
  "elements": [
    {"element": "window", "aliases": ["glass", "glazing", ...]},
    ...
  ]
}
```

### Meeting Glossary (`config/meeting_glossary.json`)
Project team structure, responsibility mapping, and task priorities.

```json
{
  "projects": {
    "Residential Tower A": {
      "team_leads": {...},
      "disciplines": {...},
      "spaces": {
        "Studio 504": {
          "responsible_role": "Unit Designer",
          "responsible_email": "alice@company.com"
        }
      }
    }
  }
}
```

## Data Models

All models are Pydantic-based for validation and serialization.

### ArchitecturalChange
```python
class ArchitecturalChange(BaseModel):
    change_id: str
    project: str
    space: str  # e.g., "Studio 504"
    element_type: str  # e.g., "window"
    action: str  # e.g., "resize"
    description: str
    confidence: float  # 0.0 - 1.0
    speaker: str
    affected_elements: list[str]  # Revit ElementIds
```

### BIMElement
```python
class BIMElement(BaseModel):
    element_id: str  # Revit ElementId
    element_type: str
    space_name: str
    family: str
    current_properties: dict
    location: dict
    level: str
```

### RevisionMarker
```python
class RevisionMarker(BaseModel):
    revision_id: str
    revit_element_id: str
    comment_text: str
    requested_by: str
    applied: bool
    applied_at: datetime
    cloud_id: str  # Revit RevisionCloud ElementId
```

## Database Schema

New tables added to SQLite database:

- **meetings**: Meeting metadata, participants, transcript
- **architectural_changes**: Detected design changes with confidence scores
- **task_assignments**: Assigned tasks with deadlines and status
- **revisions**: Applied Revit revision clouds with metadata

See `schema.py` for complete schema and setup instructions.

## Training Data

Sample meeting transcripts in JSONL format:

```jsonl
{"timestamp": "10:21:32", "speaker": "Architect_A", "text": "We need to increase the window size in Studio Unit 504.", "action": "resize", "space": "Studio 504", "element": "window"}
{"timestamp": "10:24:15", "speaker": "Architect_B", "text": "The corridor wall should move 300mm to the south.", "action": "move", "space": "Corridor B", "element": "wall"}
```

Located in `data/meeting_transcripts_training.jsonl`.

## API Endpoints (Future)

```
GET /api/meetings
  List all meetings

GET /api/meetings/{meeting_id}
  Get meeting details and transcript

GET /api/meetings/{meeting_id}/decisions
  Get all design changes from meeting

POST /api/tasks/{task_id}/status
  Update task status

GET /api/dashboard/summary
  KPIs and overview

POST /api/revisions/create
  Create revision in Revit
```

## Integration Points

### With Existing GigAI

1. **Orchestrator** (`orchestrator.py`)
   - Feeds decision packages into pipeline
   - Receives authority decisions (auto/manual)
   - Executes via existing action gateway

2. **Event Bus** (`event_bus.py`)
   - Emits meeting.processed, revision.executed events
   - Subscribes to approval.completed events

3. **Storage** (`storage.py`)
   - Persists meetings, changes, tasks, revisions
   - Audit logging for all operations

4. **Fireflies** (`fireflies_stt.py`)
   - Fetches meeting transcripts
   - Extracts speaker diarization
   - Provides transcript URLs

5. **Google Calendar** (`google_calendar.py`)
   - Extracts meeting participants
   - Creates task calendar events
   - Updates task deadlines

6. **BIM360** (`bim360_client.py`)
   - Writes revision decisions as issues
   - Attaches meeting minutes and transcripts
   - Cross-references Revit elements

## Usage Examples

### Example 1: Process a Meeting

```python
from gigai.meeting_intelligence import MeetingEventProcessor

processor = MeetingEventProcessor()

# Process meeting from Fireflies
result = await processor.process_meeting_from_fireflies(
    fireflies_meeting_id="ff_meeting_001",
    project_id="proj_tower_a",
    project_name="Residential Tower A"
)

# Check results
print(f"Changes detected: {len(result.architectural_changes)}")
for change in result.architectural_changes:
    print(f"  - {change.space}: {change.action} {change.element_type}")
    print(f"    Confidence: {change.confidence:.0%}")
    print(f"    Description: {change.description}")
```

### Example 2: Map Changes to BIM Elements

```python
from gigai.meeting_intelligence import BIMElementIdentifier

identifier = BIMElementIdentifier()

for change in result.architectural_changes:
    elements = identifier.find_elements_for_change(change)
    print(f"\nChange affects {len(elements)} elements:")
    for elem in elements:
        print(f"  - {elem.element_id} ({elem.family})")
        print(f"    Properties: {elem.current_properties}")
```

### Example 3: Create Revit Revisions

```python
from gigai.meeting_intelligence import RevisionExecutor

executor = RevisionExecutor()

for change in result.architectural_changes:
    revision = await executor.execute_revision(
        change=change,
        decision_id="d_123",
        project_id="proj_tower_a",
        meeting_id=result.meeting_id,
        requested_by=change.speaker
    )

    if revision and revision.applied:
        print(f"✓ Revision {revision.cloud_id} applied to Revit")
```

## Testing

### Unit Tests
```bash
pytest tests/meeting_intelligence/test_architectural_parser.py
pytest tests/meeting_intelligence/test_bim_identifier.py
pytest tests/meeting_intelligence/test_meeting_processor.py
```

### Integration Tests
```bash
pytest tests/meeting_intelligence/test_integration.py
```

### E2E Testing
```python
# test_e2e_meeting_flow.py
async def test_full_meeting_to_revit_flow():
    # Upload transcript
    # Verify changes extracted
    # Check BIM element mapping
    # Confirm Revit revisions created
    # Validate task assignments
    # Check email notifications
    pass
```

## Roadmap

### Phase 1 (Complete ✓)
- [x] Architectural NLP parser
- [x] Meeting processor
- [x] BIM element identifier
- [x] Revit REST client
- [x] Revision executor
- [x] Decision agent

### Phase 2 (In Progress)
- [ ] C# Revit add-in with direct API
- [ ] pyRevit automation scripts
- [ ] Task assignment and email automation
- [ ] Meeting minutes generator
- [ ] Dashboard API endpoints

### Phase 3 (Planned)
- [ ] React/Next.js dashboard
- [ ] Real-time WebSocket updates
- [ ] Advanced ML for NLP
- [ ] Multi-language support
- [ ] Integration with Slack/Teams

## Architecture Decision Records

### 1. Local NLP vs External LLM
**Decision**: Use local fuzzy matching + domain vocabulary
**Rationale**: Fast, deterministic, no API latency, fully offline capable

### 2. Mock BIM Data vs Real Revit API
**Decision**: Start with mock, abstract with REST client for easy swap
**Rationale**: Faster MVP, easier testing, allows parallel development

### 3. Fully Integrated vs Standalone
**Decision**: Fully integrated with GigAI orchestrator
**Rationale**: Single source of truth, reuse existing pipeline, consistent audit trail

## Performance Targets

- **Transcript processing**: < 2 seconds for 1-hour meeting
- **Change detection accuracy**: > 85% (with human review)
- **Revit revision placement**: < 30 seconds after approval
- **Email notifications**: < 2 minutes after task assignment
- **Database queries**: < 100ms for meeting lookups

## License

Part of GigAI - Proprietary
