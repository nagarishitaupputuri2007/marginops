"""AI Investigator & Human Approval Gate REST endpoints (Slide 06)."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field

from app.services.investigator import ApprovalActionCard, InvestigationReport
from app.services.platform_state import PlatformStateService

router = APIRouter(prefix="/investigations", tags=["AI Investigator & Governance"])


class InvestigationDecisionRequest(BaseModel):
    """Payload for human approval, rejection, or dismissal actions."""
    reviewer_email: str = Field(..., json_schema_extra={"example": "finops-lead@acme.com"}, description="Identity of reviewer")
    notes: Optional[str] = Field(default=None, json_schema_extra={"example": "Approved per FinOps policy"}, description="Reviewer notes")


@router.get("", response_model=List[InvestigationReport])
async def list_investigations() -> List[InvestigationReport]:
    """Retrieves all AI investigation reports with cited evidence and recommendations."""
    state = PlatformStateService.get_instance()
    return state.get_investigations()


@router.get("/{investigation_id}", response_model=InvestigationReport)
async def get_investigation(
    investigation_id: uuid.UUID = Path(..., description="Unique investigation UUID"),
) -> InvestigationReport:
    """Retrieves a single investigation report by its UUID."""
    state = PlatformStateService.get_instance()
    report = state.get_investigation_by_id(investigation_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found",
        )
    return report


@router.post("/{investigation_id}/approve", response_model=ApprovalActionCard)
async def approve_investigation(
    investigation_id: uuid.UUID = Path(..., description="Unique investigation UUID"),
    decision: InvestigationDecisionRequest = ...,
) -> ApprovalActionCard:
    """Governed Human Approval Gate: Approves the investigator's recommended remediation.
    
    Verifies reviewer identity, seals cryptographic SHA-256 audit fingerprint, and commits decision.
    """
    state = PlatformStateService.get_instance()
    card = state.approve_investigation(
        investigation_id=investigation_id,
        reviewer_email=decision.reviewer_email,
        notes=decision.notes,
    )
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found",
        )
    return card


@router.post("/{investigation_id}/reject", response_model=ApprovalActionCard)
async def reject_investigation(
    investigation_id: uuid.UUID = Path(..., description="Unique investigation UUID"),
    decision: InvestigationDecisionRequest = ...,
) -> ApprovalActionCard:
    """Rejects the investigator's recommended remediation with mandatory review notes."""
    state = PlatformStateService.get_instance()
    card = state.reject_investigation(
        investigation_id=investigation_id,
        reviewer_email=decision.reviewer_email,
        notes=decision.notes,
    )
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found",
        )
    return card


@router.post("/{investigation_id}/dismiss", response_model=ApprovalActionCard)
async def dismiss_investigation(
    investigation_id: uuid.UUID = Path(..., description="Unique investigation UUID"),
    decision: InvestigationDecisionRequest = ...,
) -> ApprovalActionCard:
    """Dismisses the investigation as an expected anomaly or false positive."""
    state = PlatformStateService.get_instance()
    card = state.dismiss_investigation(
        investigation_id=investigation_id,
        reviewer_email=decision.reviewer_email,
        notes=decision.notes,
    )
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found",
        )
    return card
