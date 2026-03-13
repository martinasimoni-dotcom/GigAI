"""
Domain processing package — DOM-06.
"""
from src.system.domain_processing.policy_engine import PolicyResult, evaluate_policies
from src.system.domain_processing.processor import ProcessingResult, process_event
from src.system.domain_processing.signal_generator import generate_signals
from src.system.domain_processing.time_analysis import TimeAnalysisResult, analyze_time

__all__ = [
    "ProcessingResult",
    "process_event",
    "generate_signals",
    "PolicyResult",
    "evaluate_policies",
    "TimeAnalysisResult",
    "analyze_time",
]
