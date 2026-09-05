import uuid
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

from src.agents.extractor import DocumentExtractorAgent, ExtractedInvoice
from src.agents.auditor import PolicyAuditorAgent, ComplianceReport
from src.ledger.manager import LedgerManager

logger = logging.getLogger(__name__)

# In-memory store for pending manager review submissions
# Key: submission_id, Value: Dict
pending_submissions_store: Dict[str, Dict[str, Any]] = {}


class ApprovalOrchestrator:
    """Agent 3: Coordinates extraction, policy auditing, manager decision dispatch, and audit logging."""

    def __init__(
        self,
        extractor: Optional[DocumentExtractorAgent] = None,
        auditor: Optional[PolicyAuditorAgent] = None,
        ledger: Optional[LedgerManager] = None,
    ):
        self.extractor = extractor or DocumentExtractorAgent()
        self.auditor = auditor or PolicyAuditorAgent()
        self.ledger = ledger or LedgerManager()

    async def audit_submitted_document(
        self,
        file_data: Union[bytes, str, Path],
        mime_type: str = "image/png",
        submitter: str = "Employee",
    ) -> Dict[str, Any]:
        """
        Runs complete pipeline: Vision Extraction -> Policy Audit -> Pending Review registration.
        """
        # 1. Agent 1: Multimodal Vision Extraction
        invoice: ExtractedInvoice = await self.extractor.extract_from_file(file_data, mime_type=mime_type)

        # 2. Agent 2: Policy & Compliance Audit
        compliance: ComplianceReport = self.auditor.audit_invoice(invoice)

        # 3. Register submission for HITL action
        submission_id = f"SUB-{uuid.uuid4().hex[:8].upper()}"
        submission_record = {
            "submission_id": submission_id,
            "submitter": submitter,
            "invoice": invoice,
            "compliance": compliance,
            "status": "PENDING_MANAGER_REVIEW",
        }
        pending_submissions_store[submission_id] = submission_record

        logger.info(
            f"Processed document for {invoice.vendor_name} (${invoice.total_amount}). Status: {compliance.status} (ID: {submission_id})"
        )

        return submission_record

    def apply_decision(
        self,
        submission_id: str,
        decision: str,  # "APPROVED", "REJECTED", "FLAGGED"
        approver: str = "Manager",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Applies manager decision, updates ledger, and closes submission."""
        record = pending_submissions_store.get(submission_id)
        if not record:
            return {
                "success": False,
                "error": f"Submission ID '{submission_id}' not found or session has expired.",
            }

        invoice: ExtractedInvoice = record["invoice"]
        compliance: ComplianceReport = record["compliance"]
        submitter = record.get("submitter", "Employee")

        # Record in official Excel ledger
        ledger_result = self.ledger.record_expense(
            invoice=invoice,
            compliance=compliance,
            decision=decision,
            approver=approver,
            submitter=submitter,
            notes=notes,
        )

        record["status"] = decision.upper()
        record["decision_details"] = {
            "decision": decision.upper(),
            "approver": approver,
            "notes": notes,
            "transaction_id": ledger_result.get("transaction_id"),
        }

        return {
            "success": True,
            "submission_id": submission_id,
            "decision": decision.upper(),
            "transaction_id": ledger_result.get("transaction_id"),
            "ledger_download_url": ledger_result.get("download_url"),
            "vendor": invoice.vendor_name,
            "total_amount": invoice.total_amount,
        }
