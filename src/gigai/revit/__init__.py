"""
Revit Integration Module

Handles all communication with Revit:
- REST API client for querying and updating model
- Revision cloud placement and commenting
- Element identification and manipulation
"""

from .revit_rest_client import RevitRESTClient, RevitRESTServer

__all__ = ["RevitRESTClient", "RevitRESTServer"]
