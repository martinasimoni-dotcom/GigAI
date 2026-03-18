"""GigAI Meeting Intelligence package with lazy exports for optional dependencies."""

from importlib import import_module

__all__ = [
    # Models
    "ArchitecturalChange",
    "BIMElement",
    "MeetingContext",
    "MeetingMinutes",
    "TaskAssignment",
    "RevisionMarker",
    "MeetingIntelligenceResult",
    # Core Processors
    "ArchitecturalNLPParser",
    "MeetingEventProcessor",
    "BIMElementIdentifier",
    "RevisionExecutor",
    # Phase 2B: Task & Communication
    "TaskAssigner",
    "EmailNotifier",
    "MeetingMinutesGenerator",
    # Agents
    "DesignChangeAgent",
    # Integration
    "integrate_meeting_into_pipeline",
    # Database
    "create_meeting_intelligence_tables",
    "add_sample_data",
]

__version__ = "0.2.0"  # Phase 2B Complete


_LAZY_EXPORTS = {
  # models
  "ArchitecturalChange": ".models",
  "BIMElement": ".models",
  "MeetingContext": ".models",
  "MeetingMinutes": ".models",
  "TaskAssignment": ".models",
  "RevisionMarker": ".models",
  "MeetingIntelligenceResult": ".models",
  # core processors
  "ArchitecturalNLPParser": ".architectural_parser",
  "MeetingEventProcessor": ".meeting_processor",
  "BIMElementIdentifier": ".bim_identifier",
  "RevisionExecutor": ".revision_executor",
  # task + comms
  "TaskAssigner": ".task_assignment",
  "EmailNotifier": ".email_notifier",
  "MeetingMinutesGenerator": ".meeting_minutes_generator",
  # agent + integration
  "DesignChangeAgent": ".meeting_decision_agent",
  "integrate_meeting_into_pipeline": ".meeting_decision_agent",
  # schema
  "create_meeting_intelligence_tables": ".schema",
  "add_sample_data": ".schema",
}


def __getattr__(name: str):
  module_name = _LAZY_EXPORTS.get(name)
  if module_name is None:
    raise AttributeError(f"module 'gigai.meeting_intelligence' has no attribute '{name}'")

  module = import_module(module_name, __name__)
  value = getattr(module, name)
  globals()[name] = value
  return value
