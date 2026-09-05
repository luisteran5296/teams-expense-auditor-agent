from typing import Dict, Any, Optional
from src.agents.extractor import ExtractedInvoice
from src.agents.auditor import ComplianceReport


def create_manager_approval_card(
    submission_id: str,
    invoice: ExtractedInvoice,
    compliance: ComplianceReport,
    submitter: str = "Employee",
) -> Dict[str, Any]:
    """
    Creates an interactive Adaptive Card for managers to review and approve/reject expenses.
    """
    # Header styling based on compliance
    if compliance.status == "COMPLIANT":
        header_color = "good"
        badge_icon = "🟢"
        status_title = "Compliant with Corporate Policy"
    elif compliance.status == "FLAGGED_WARNING":
        header_color = "warning"
        badge_icon = "🟡"
        status_title = "Warnings Detected - Discretionary Review"
    else:
        header_color = "attention"
        badge_icon = "🔴"
        status_title = "Policy Violations Detected"

    # Line items display
    line_item_blocks = []
    for item in invoice.line_items[:8]:
        is_flagged = item.category.lower() == "alcohol"
        flag_tag = " [⚠️ RESTRICTED: Alcohol]" if is_flagged else ""
        line_item_blocks.append({
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"• {item.description}{flag_tag}",
                            "size": "Small",
                            "color": "Attention" if is_flagged else "Default",
                            "weight": "Bolder" if is_flagged else "Lighter",
                        }
                    ],
                },
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"${item.total_price:.2f}",
                            "size": "Small",
                            "weight": "Bolder",
                        }
                    ],
                },
            ],
        })

    # Violations / Warnings block
    violations_block = []
    if compliance.violations:
        violation_texts = []
        for v in compliance.violations:
            icon = "🔴" if v.severity == "CRITICAL" else ("🟡" if v.severity == "WARNING" else "ℹ️")
            violation_texts.append({
                "type": "TextBlock",
                "text": f"{icon} **{v.rule_name}:** {v.message}\n*{v.suggested_action}*",
                "wrap": True,
                "size": "Small",
                "spacing": "Small",
            })

        violations_block = [
            {
                "type": "Container",
                "style": "emphasis",
                "spacing": "Medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "📋 **Audit Findings & Policy Checks:**",
                        "weight": "Bolder",
                        "size": "Small",
                    },
                    *violation_texts,
                ],
            }
        ]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "Container",
                "style": header_color,
                "bleed": True,
                "items": [
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "🧾",
                                        "size": "ExtraLarge",
                                    }
                                ],
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"{badge_icon} Expense Review: {invoice.vendor_name}",
                                        "weight": "Bolder",
                                        "size": "Medium",
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": f"Submitted by: {submitter} | Ref: {submission_id}",
                                        "isSubtle": True,
                                        "spacing": "None",
                                    },
                                ],
                            },
                        ],
                    }
                ],
            },
            {
                "type": "FactSet",
                "spacing": "Medium",
                "facts": [
                    {"title": "Vendor / Merchant:", "value": invoice.vendor_name},
                    {"title": "Date of Expense:", "value": invoice.date},
                    {"title": "Category:", "value": invoice.category},
                    {"title": "Grand Total:", "value": f"${invoice.total_amount:.2f} {invoice.currency}"},
                    {"title": "Compliance Status:", "value": status_title},
                    {"title": "Risk Score:", "value": f"{compliance.risk_score} / 100"},
                ],
            },
            {
                "type": "TextBlock",
                "text": "🛒 **Itemized Purchases:**",
                "weight": "Bolder",
                "size": "Small",
                "spacing": "Medium",
            },
            *line_item_blocks,
            *violations_block,
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "✅ Approve Expense",
                "style": "positive",
                "data": {
                    "action": "manager_approve",
                    "submission_id": submission_id,
                },
            },
            {
                "type": "Action.Submit",
                "title": "❌ Reject Expense",
                "style": "destructive",
                "data": {
                    "action": "manager_reject",
                    "submission_id": submission_id,
                },
            },
            {
                "type": "Action.Submit",
                "title": "⚠️ Request Clarification",
                "data": {
                    "action": "manager_flag",
                    "submission_id": submission_id,
                },
            },
        ],
    }


def create_decision_receipt_card(
    decision: str,
    transaction_id: Optional[str],
    vendor: str,
    amount: float,
    approver: str,
    ledger_url: str,
) -> Dict[str, Any]:
    """Card confirming manager decision and providing link to the updated audit ledger."""
    is_approved = decision.upper() == "APPROVED"
    header_style = "good" if is_approved else "attention"
    title_text = "Expense Approved & Logged ✅" if is_approved else "Expense Rejected ❌"

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "Container",
                "style": header_style,
                "bleed": True,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": title_text,
                        "weight": "Bolder",
                        "size": "Medium",
                    },
                    {
                        "type": "TextBlock",
                        "text": f"Transaction ID: {transaction_id or 'N/A'}",
                        "isSubtle": True,
                        "spacing": "None",
                    },
                ],
            },
            {
                "type": "FactSet",
                "spacing": "Medium",
                "facts": [
                    {"title": "Vendor:", "value": vendor},
                    {"title": "Total Amount:", "value": f"${amount:.2f}"},
                    {"title": "Decision By:", "value": approver},
                    {"title": "Audit Trail:", "value": "Recorded in Official Expense Ledger"},
                ],
            },
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "📥 Download Excel Audit Ledger",
                "style": "positive",
                "url": ledger_url,
            }
        ],
    }
