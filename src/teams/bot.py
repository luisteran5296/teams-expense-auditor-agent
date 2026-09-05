import logging
import re
from typing import List, Dict, Any

from botbuilder.core import ActivityHandler, TurnContext, MessageFactory, CardFactory
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount, Attachment

from src.config import settings
from src.agents.approval import ApprovalOrchestrator
from src.teams.cards import (
    create_manager_approval_card,
    create_decision_receipt_card,
)
from src.teams.threading import apply_threading
from src.teams.files import TeamsFileManager

logger = logging.getLogger(__name__)


class ExpenseAuditorTeamsBot(ActivityHandler):
    """
    Microsoft Teams Bot for Multi-Agent Invoice & Expense Auditing.
    Coordinates Multimodal Vision extraction, policy compliance checking, and manager approval cards.
    """

    def __init__(self, orchestrator: ApprovalOrchestrator):
        super().__init__()
        self.orchestrator = orchestrator

    def _clean_user_text(self, turn_context: TurnContext) -> str:
        """Strips @mentions tags and excess whitespace from incoming message."""
        text = turn_context.activity.text or ""
        cleaned = re.sub(r"<at>.*?</at>", "", text, flags=re.IGNORECASE)
        return cleaned.strip()

    async def on_message_activity(self, turn_context: TurnContext):
        activity = turn_context.activity
        sender_name = getattr(activity.from_property, "name", "Colleague")

        # 1. Handle Adaptive Card Action Submissions (Manager clicks Approve / Reject)
        if activity.value and isinstance(activity.value, dict):
            await self._handle_card_action(turn_context, activity.value, sender_name)
            return

        # 2. Handle Attached Receipts / Invoices (Images or PDFs)
        if activity.attachments and len(activity.attachments) > 0:
            handled = await self._handle_file_attachments(turn_context, activity.attachments, sender_name)
            if handled:
                return

        # 3. Clean message text
        query = self._clean_user_text(turn_context)
        logger.info(f"Received message in Teams: '{query}'")

        if not query or query.lower() in ("help", "menu", "start", "policy", "policies"):
            await self._send_help_card(turn_context)
            return

        # Check for sample test commands (e.g. 'sample 1', 'test 2')
        sample_match = re.search(r"(?:sample|test)\s*([1-4])", query, re.IGNORECASE)
        if sample_match:
            sample_id = sample_match.group(1)
            sample_map = {
                "1": ("1_compliant_hotel_stay.pdf", "application/pdf"),
                "2": ("2_flagged_executive_dinner_alcohol.pdf", "application/pdf"),
                "3": ("3_high_value_it_equipment_requires_po.pdf", "application/pdf"),
                "4": ("4_compliant_flight_receipt.pdf", "application/pdf"),
            }
            fname, mime = sample_map.get(sample_id, ("1_compliant_hotel_stay.pdf", "application/pdf"))
            fpath = settings.SAMPLES_DIR / fname
            if fpath.exists():
                try:
                    await turn_context.send_activity(Activity(type=ActivityTypes.typing))
                except Exception:
                    pass
                result = await self.orchestrator.audit_submitted_document(
                    file_data=fpath,
                    mime_type=mime,
                    submitter=sender_name,
                )
                approval_card = create_manager_approval_card(
                    submission_id=result["submission_id"],
                    invoice=result["invoice"],
                    compliance=result["compliance"],
                    submitter=sender_name,
                )
                reply = MessageFactory.attachment(CardFactory.adaptive_card(approval_card))
                apply_threading(activity, reply)
                await turn_context.send_activity(reply)
                return

        # 4. Check for ledger inquiry
        if any(w in query.lower() for w in ("ledger", "summary", "audit", "totals", "spend")):
            stats = self.orchestrator.ledger.get_summary_statistics()
            download_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ledgers/expense_audit_ledger.xlsx"
            msg = (
                f"📊 **Corporate Expense Audit Ledger Status:**\n\n"
                f"• **Total Processed Transactions:** {stats.get('total_records', 0)}\n"
                f"• **Approved Expenditures:** ${stats.get('total_approved_spend_usd', 0.0):,.2f}\n"
                f"• **Approved Count:** {stats.get('approved_count', 0)} | **Rejected Count:** {stats.get('rejected_count', 0)}\n\n"
                f"[📥 **Download Full Excel Audit Ledger**]({download_url})"
            )
            reply = MessageFactory.text(msg)
            apply_threading(activity, reply)
            await turn_context.send_activity(reply)
            return

        # 5. Send typing indicator for general questions
        try:
            typing_activity = Activity(type=ActivityTypes.typing)
            apply_threading(activity, typing_activity)
            await turn_context.send_activity(typing_activity)
        except Exception:
            pass

        # 6. Conversational answer about policies
        reply_text = (
            f"👋 Hello {sender_name}! I am your **Multi-Agent Expense & Invoice Auditor**.\n\n"
            f"Here is how to use me:\n"
            f"1. **Drag and drop any receipt or invoice** (image or PDF) into this chat.\n"
            f"2. Our **Vision Agent** will extract line items and vendor details.\n"
            f"3. Our **Auditor Agent** will cross-reference it with corporate spending limits.\n"
            f"4. An **Interactive Approval Card** will be generated with 1-click decision buttons for managers!"
        )
        reply = MessageFactory.text(reply_text)
        apply_threading(activity, reply)
        await turn_context.send_activity(reply)

    async def _handle_card_action(
        self, turn_context: TurnContext, card_data: Dict[str, Any], approver_name: str
    ):
        """Processes manager approval, rejection, or clarification requests."""
        action = card_data.get("action")
        submission_id = card_data.get("submission_id", "")
        logger.info(f"Card action: {action} on submission {submission_id} by {approver_name}")

        if action == "manager_approve":
            res = self.orchestrator.apply_decision(
                submission_id=submission_id,
                decision="APPROVED",
                approver=approver_name,
                notes="Approved via Teams Adaptive Card",
            )
            if res.get("success"):
                receipt_card = create_decision_receipt_card(
                    decision="APPROVED",
                    transaction_id=res.get("transaction_id"),
                    vendor=res.get("vendor", "Merchant"),
                    amount=res.get("total_amount", 0.0),
                    approver=approver_name,
                    ledger_url=res.get("ledger_download_url", "#"),
                )
                reply = MessageFactory.attachment(CardFactory.adaptive_card(receipt_card))
            else:
                reply = MessageFactory.text(f"⚠️ {res.get('error', 'Could not process approval.')}")

            apply_threading(turn_context.activity, reply)
            await turn_context.send_activity(reply)

        elif action == "manager_reject":
            res = self.orchestrator.apply_decision(
                submission_id=submission_id,
                decision="REJECTED",
                approver=approver_name,
                notes="Rejected by manager via Teams Adaptive Card",
            )
            if res.get("success"):
                receipt_card = create_decision_receipt_card(
                    decision="REJECTED",
                    transaction_id=res.get("transaction_id"),
                    vendor=res.get("vendor", "Merchant"),
                    amount=res.get("total_amount", 0.0),
                    approver=approver_name,
                    ledger_url=res.get("ledger_download_url", "#"),
                )
                reply = MessageFactory.attachment(CardFactory.adaptive_card(receipt_card))
            else:
                reply = MessageFactory.text(f"⚠️ {res.get('error', 'Could not process rejection.')}")

            apply_threading(turn_context.activity, reply)
            await turn_context.send_activity(reply)

        elif action == "manager_flag":
            reply = MessageFactory.text(
                f"⚠️ Submission `{submission_id}` has been flagged for employee clarification. Notification sent."
            )
            apply_threading(turn_context.activity, reply)
            await turn_context.send_activity(reply)

        elif action == "audit_sample":
            sample_id = str(card_data.get("sample_id", "1"))
            sample_map = {
                "1": ("1_compliant_hotel_stay.pdf", "application/pdf"),
                "2": ("2_flagged_executive_dinner_alcohol.pdf", "application/pdf"),
                "3": ("3_high_value_it_equipment_requires_po.pdf", "application/pdf"),
                "4": ("4_compliant_flight_receipt.pdf", "application/pdf"),
            }
            fname, mime = sample_map.get(sample_id, ("1_compliant_hotel_stay.pdf", "application/pdf"))
            fpath = settings.SAMPLES_DIR / fname
            if fpath.exists():
                try:
                    await turn_context.send_activity(Activity(type=ActivityTypes.typing))
                except Exception:
                    pass
                result = await self.orchestrator.audit_submitted_document(
                    file_data=fpath,
                    mime_type=mime,
                    submitter=approver_name,
                )
                approval_card = create_manager_approval_card(
                    submission_id=result["submission_id"],
                    invoice=result["invoice"],
                    compliance=result["compliance"],
                    submitter=approver_name,
                )
                reply = MessageFactory.attachment(CardFactory.adaptive_card(approval_card))
                apply_threading(turn_context.activity, reply)
                await turn_context.send_activity(reply)

        elif action == "view_ledger_stats":
            stats = self.orchestrator.ledger.get_summary_statistics()
            download_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ledgers/expense_audit_ledger.xlsx"
            msg = (
                f"📊 **Corporate Expense Audit Ledger Status:**\n\n"
                f"• **Total Processed Transactions:** {stats.get('total_records', 0)}\n"
                f"• **Approved Expenditures:** ${stats.get('total_approved_spend_usd', 0.0):,.2f}\n"
                f"• **Approved Count:** {stats.get('approved_count', 0)} | **Rejected Count:** {stats.get('rejected_count', 0)}\n\n"
                f"[📥 **Download Full Excel Audit Ledger**]({download_url})"
            )
            reply = MessageFactory.text(msg)
            apply_threading(turn_context.activity, reply)
            await turn_context.send_activity(reply)

    async def _handle_file_attachments(
        self, turn_context: TurnContext, attachments: List[Attachment], submitter: str
    ) -> bool:
        """Processes receipt/invoice image attachments."""
        valid_extensions = (".png", ".jpg", ".jpeg", ".webp", ".pdf")
        for att in attachments:
            filename = att.name or "receipt.png"
            if any(filename.lower().endswith(ext) for ext in valid_extensions):
                # Teams file uploads expose the downloadable bytes separately
                # from content_url, which points to the SharePoint file page.
                if att.content_type == "application/vnd.microsoft.teams.file.download.info":
                    content = att.content if isinstance(att.content, dict) else {}
                    content_url = content.get("downloadUrl")
                else:
                    content_url = att.content_url
                if not content_url:
                    await turn_context.send_activity(
                        MessageFactory.text(f"⚠️ No download URL for `{filename}`. Please upload the file again in a personal chat.")
                    )
                    return True

                # Send typing indicator
                try:
                    await turn_context.send_activity(Activity(type=ActivityTypes.typing))
                except Exception:
                    pass

                # Download bytes
                file_bytes = await TeamsFileManager.download_attachment(content_url)
                if not file_bytes:
                    await turn_context.send_activity(
                        MessageFactory.text(f"⚠️ Could not download attachment `{filename}`.")
                    )
                    return True

                # Determine MIME type
                mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/png"
                if filename.lower().endswith((".jpg", ".jpeg")):
                    mime_type = "image/jpeg"
                elif filename.lower().endswith(".webp"):
                    mime_type = "image/webp"

                # Run Multi-Agent Extraction & Policy Audit
                result = await self.orchestrator.audit_submitted_document(
                    file_data=file_bytes,
                    mime_type=mime_type,
                    submitter=submitter,
                )

                approval_card = create_manager_approval_card(
                    submission_id=result["submission_id"],
                    invoice=result["invoice"],
                    compliance=result["compliance"],
                    submitter=submitter,
                )

                reply = MessageFactory.attachment(CardFactory.adaptive_card(approval_card))
                apply_threading(turn_context.activity, reply)
                await turn_context.send_activity(reply)
                return True

        return False

    async def _send_help_card(self, turn_context: TurnContext):
        """Sends an interactive help and policy guide card."""
        rules = self.orchestrator.auditor.policy.get("rules", {})
        meal_max = rules.get("meals_and_entertainment", {}).get("max_per_person_usd", 75.0)
        sw_max = rules.get("software_and_saas", {}).get("max_direct_expense_usd", 500.0)
        gen_max = rules.get("general", {}).get("max_unapproved_transaction_usd", 1000.0)

        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🧾 **Multi-Agent Invoice & Expense Auditor**",
                    "size": "Medium",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": "Upload any receipt or invoice to extract line items, check corporate policies, and generate manager approval workflows.",
                    "wrap": True,
                    "isSubtle": True,
                },
                {
                    "type": "FactSet",
                    "spacing": "Medium",
                    "facts": [
                        {"title": "🍽️ Meals Limit:", "value": f"Up to ${meal_max:.2f} per person (Alcohol prohibited)"},
                        {"title": "💻 Software / SaaS:", "value": f"Up to ${sw_max:.2f} direct expense"},
                        {"title": "🚨 Threshold limit:", "value": f"Purchases >${gen_max:,.2f} require prior PO"},
                        {"title": "📑 Supported Files:", "value": "PNG, JPG, WEBP, PDF receipts"},
                    ],
                },
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🟢 Test Sample 1: Hotel ($425.80)",
                    "data": {"action": "audit_sample", "sample_id": "1"},
                },
                {
                    "type": "Action.Submit",
                    "title": "🔴 Test Sample 2: Alcohol Dinner ($357.12)",
                    "data": {"action": "audit_sample", "sample_id": "2"},
                },
                {
                    "type": "Action.Submit",
                    "title": "🔴 Test Sample 3: IT Hardware ($1,440.88)",
                    "data": {"action": "audit_sample", "sample_id": "3"},
                },
                {
                    "type": "Action.Submit",
                    "title": "📊 View Current Expense Ledger",
                    "data": {"action": "view_ledger_stats"},
                },
            ],
        }
        reply = MessageFactory.attachment(CardFactory.adaptive_card(card))
        apply_threading(turn_context.activity, reply)
        await turn_context.send_activity(reply)

    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        """Sends welcome greeting when bot is added."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self._send_help_card(turn_context)
