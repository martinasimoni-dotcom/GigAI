"""
Revit REST API Client

Communication wrapper for Revit operations:
- Query spaces and elements
- Place revision clouds
- Attach comments
- Update shared parameters

Supports both direct Revit server (if available) and C# add-in REST endpoints.
"""

import json
import logging
import asyncio
from typing import Optional
from datetime import datetime
import httpx

from .models import BIMElement, RevisionMarker

logger = logging.getLogger(__name__)


class RevitRESTClient:
    """
    REST client for communicating with Revit.

    Connects to:
    1. Local Revit REST server (running on port 8000)
    2. C# Add-in HTTP endpoints
    3. Remote Revit server via API
    """

    def __init__(
        self,
        revit_server_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Revit REST client.

        Args:
            revit_server_url: URL to Revit REST server
            timeout: Request timeout in seconds
            api_key: Optional API key for authenticated endpoints
        """
        self.base_url = revit_server_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=timeout)

    async def health_check(self) -> bool:
        """
        Check if Revit server is running and responsive.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_all_spaces(self, project_id: Optional[str] = None) -> list[dict]:
        """
        Get all spaces (rooms) in the Revit model.

        Args:
            project_id: Optional project filter

        Returns:
            List of space data
        """
        try:
            params = {}
            if project_id:
                params["project_id"] = project_id

            response = await self.client.get(f"{self.base_url}/api/spaces", params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved {len(data.get('spaces', []))} spaces")
            return data.get("spaces", [])

        except Exception as e:
            logger.error(f"Error getting spaces: {e}")
            return []

    async def get_elements_in_space(self, space_id: str, element_type: Optional[str] = None) -> list[BIMElement]:
        """
        Get all elements in a specific space.

        Args:
            space_id: Revit room ElementId
            element_type: Optional filter (window, door, wall, etc.)

        Returns:
            List of BIM elements
        """
        try:
            params = {}
            if element_type:
                params["type"] = element_type

            response = await self.client.get(f"{self.base_url}/api/spaces/{space_id}/elements", params=params)
            response.raise_for_status()

            data = response.json()
            elements = []

            for elem_data in data.get("elements", []):
                elements.append(BIMElement(
                    element_id=elem_data["element_id"],
                    element_type=elem_data.get("type"),
                    space_name=elem_data.get("space_name"),
                    space_id=space_id,
                    family=elem_data.get("family"),
                    current_properties=elem_data.get("properties", {}),
                    parameters=elem_data.get("parameters", {}),
                    level=elem_data.get("level"),
                ))

            logger.info(f"Retrieved {len(elements)} elements in space {space_id}")
            return elements

        except Exception as e:
            logger.error(f"Error getting elements in space {space_id}: {e}")
            return []

    async def get_element(self, element_id: str) -> Optional[BIMElement]:
        """
        Get a specific element by ID.

        Args:
            element_id: Revit ElementId

        Returns:
            BIM element data or None
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/elements/{element_id}")
            response.raise_for_status()

            data = response.json()
            return BIMElement(
                element_id=data["element_id"],
                element_type=data.get("type"),
                space_name=data.get("space_name"),
                family=data.get("family"),
                current_properties=data.get("properties", {}),
                parameters=data.get("parameters", {}),
                level=data.get("level"),
            )

        except Exception as e:
            logger.error(f"Error getting element {element_id}: {e}")
            return None

    async def create_revision_cloud(self, revision: RevisionMarker) -> Optional[str]:
        """
        Create a revision cloud in Revit.

        Args:
            revision: RevisionMarker object with details

        Returns:
            Revit RevisionCloud ElementId, or None if failed
        """
        try:
            payload = {
                "element_id": revision.revit_element_id,
                "shape_type": revision.shape_type,
                "color": revision.color,
                "comment_text": revision.comment_text,
                "comment_details": revision.comment_details,
                "requested_by": revision.requested_by,
                "revision_date": revision.revision_date.isoformat(),
            }

            response = await self.client.post(
                f"{self.base_url}/api/revisions/create",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            cloud_id = data.get("cloud_id")

            logger.info(f"Created revision cloud {cloud_id} for element {revision.revit_element_id}")
            return cloud_id

        except Exception as e:
            logger.error(f"Error creating revision cloud: {e}")
            return None

    async def add_comment_to_element(
        self, element_id: str, comment_text: str, comment_details: Optional[dict] = None
    ) -> bool:
        """
        Attach a comment to an element in Revit.

        Args:
            element_id: Revit ElementId
            comment_text: Comment text
            comment_details: Optional structured comment data

        Returns:
            True if successful
        """
        try:
            payload = {
                "comment_text": comment_text,
                "comment_details": comment_details or {},
                "author": "GigAI_System",
                "timestamp": datetime.now().isoformat(),
            }

            response = await self.client.post(
                f"{self.base_url}/api/elements/{element_id}/comment",
                json=payload,
            )
            response.raise_for_status()

            logger.info(f"Added comment to element {element_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding comment to element: {e}")
            return False

    async def update_element_parameter(
        self, element_id: str, parameter_name: str, parameter_value: str
    ) -> bool:
        """
        Update a parameter on an element.

        Args:
            element_id: Revit ElementId
            parameter_name: Parameter name
            parameter_value: New parameter value

        Returns:
            True if successful
        """
        try:
            payload = {
                "parameter_name": parameter_name,
                "parameter_value": parameter_value,
                "updated_at": datetime.now().isoformat(),
            }

            response = await self.client.post(
                f"{self.base_url}/api/elements/{element_id}/parameter",
                json=payload,
            )
            response.raise_for_status()

            logger.info(f"Updated parameter {parameter_name} on element {element_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating element parameter: {e}")
            return False

    async def get_revision_clouds(self, project_id: Optional[str] = None) -> list[dict]:
        """
        Get all revision clouds in the model.

        Args:
            project_id: Optional project filter

        Returns:
            List of revision cloud data
        """
        try:
            params = {}
            if project_id:
                params["project_id"] = project_id

            response = await self.client.get(f"{self.base_url}/api/revisions", params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved {len(data.get('revisions', []))} revision clouds")
            return data.get("revisions", [])

        except Exception as e:
            logger.error(f"Error getting revision clouds: {e}")
            return []

    async def delete_revision_cloud(self, cloud_id: str) -> bool:
        """
        Delete a revision cloud from Revit.

        Args:
            cloud_id: Revit RevisionCloud ElementId

        Returns:
            True if successful
        """
        try:
            response = await self.client.delete(f"{self.base_url}/api/revisions/{cloud_id}")
            response.raise_for_status()

            logger.info(f"Deleted revision cloud {cloud_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting revision cloud: {e}")
            return False

    async def export_model_data(self, export_format: str = "json") -> Optional[bytes]:
        """
        Export model data from Revit.

        Args:
            export_format: Export format (json, ifc, dwg)

        Returns:
            Exported model data or None if failed
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/export",
                params={"format": export_format},
            )
            response.raise_for_status()

            logger.info(f"Exported model data as {export_format}")
            return response.content

        except Exception as e:
            logger.error(f"Error exporting model data: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class RevitRESTServer:
    """
    Mock Revit REST Server for testing and local development.

    This would normally run as a separate service on the same machine as Revit,
    but for MVP we provide a mock implementation that uses test data.
    """

    def __init__(self, port: int = 8000):
        """Initialize mock Revit server"""
        self.port = port
        self.app = self._create_app()

    def _create_app(self):
        """Create FastAPI app for mock Revit server"""
        try:
            from fastapi import FastAPI

            app = FastAPI(title="Revit REST Server", version="0.1.0")

            @app.get("/health")
            async def health():
                return {"status": "healthy", "service": "revit_rest_server"}

            @app.get("/api/spaces")
            async def get_spaces(project_id: Optional[str] = None):
                """Get all spaces in model"""
                return {
                    "spaces": [
                        {"space_id": "room_001", "name": "Studio 504", "level": "Level 05"},
                        {"space_id": "room_002", "name": "Corridor B", "level": "Level 05"},
                        {"space_id": "room_003", "name": "Lobby", "level": "Level 00"},
                    ]
                }

            @app.get("/api/spaces/{space_id}/elements")
            async def get_space_elements(space_id: str, type: Optional[str] = None):
                """Get elements in a space"""
                return {
                    "elements": [
                        {
                            "element_id": "window_501",
                            "type": "window",
                            "space_name": "Studio 504",
                            "family": "Fixed Window",
                        }
                    ]
                }

            @app.post("/api/revisions/create")
            async def create_revision(request_data: dict):
                """Create revision cloud"""
                return {"cloud_id": "rev_cloud_001", "status": "created"}

            @app.post("/api/elements/{element_id}/comment")
            async def add_comment(element_id: str, request_data: dict):
                """Add comment to element"""
                return {"status": "success", "element_id": element_id}

            return app

        except ImportError:
            logger.warning("FastAPI not installed, mock server not available")
            return None

    def run(self):
        """Run the mock server"""
        if self.app:
            import uvicorn

            uvicorn.run(self.app, host="0.0.0.0", port=self.port)
        else:
            logger.error("Cannot start server, FastAPI not installed")
