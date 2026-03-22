from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class ProposalOut(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: str
    confidence: Optional[float] = None
    cost: Optional[float] = None
    actions: Optional[List[Any]] = None
    proposal_data: Optional[Any] = None
    source_rfi_id: Optional[str] = None
    acc_project_id: Optional[str] = None
    assigned_user_email: Optional[str] = None
    email_sent: Optional[bool] = False
    email_sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DecisionOut(BaseModel):
    id: str
    proposal_id: str
    decision: str
    decided_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    reason: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str = ""


# -------------------------------------------------------------------------
# Webhook payloads
# -------------------------------------------------------------------------

class FirefliesWebhook(BaseModel):
    transcript: str
    title: str = "Meeting"
    participants: List[str] = []
    meeting_id: Optional[str] = None


class ACCRFIData(BaseModel):
    """RFI fields inside the ACC webhook payload."""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    assignedTo: Optional[str] = None
    assignedToType: Optional[str] = None
    assignedToEmail: Optional[str] = None
    status: Optional[str] = None
    createdAt: Optional[str] = None
    projectId: Optional[str] = None


class ACCWebhookPayload(BaseModel):
    """Inner payload from ACC event notification."""
    event: Optional[str] = None
    projectId: Optional[str] = None
    timestamp: Optional[str] = None
    data: Optional[ACCRFIData] = None


class ACCWebhook(BaseModel):
    """
    Top-level ACC webhook envelope.

    ACC sends:
      { "version": "1.0", "messageType": "notification",
        "payload": { "event": "rfis.rfi.created", "projectId": "...",
                     "data": { "id": "...", "title": "...", ... } } }

    We also accept a flat test format:
      { "event": "rfi.created", "payload": { ... } }
    """
    version: Optional[str] = None
    messageType: Optional[str] = None
    # ACC standard envelope
    payload: Optional[ACCWebhookPayload] = None
    # Flat test/legacy envelope
    event: Optional[str] = None

    def get_event(self) -> str:
        if self.payload and self.payload.event:
            return self.payload.event
        return self.event or ""

    def get_rfi_data(self) -> Optional[ACCRFIData]:
        if self.payload and self.payload.data:
            return self.payload.data
        return None

    def get_project_id(self) -> Optional[str]:
        if self.payload:
            if self.payload.projectId:
                return self.payload.projectId
            if self.payload.data and self.payload.data.projectId:
                return self.payload.data.projectId
        return None
