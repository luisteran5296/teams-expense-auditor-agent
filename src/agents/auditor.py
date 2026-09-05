import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field

from src.config import settings
from src.agents.extractor import ExtractedInvoice

logger = logging.getLogger(__name__)


class PolicyViolation(BaseModel):
    rule_name: str
    severity: str = Field(description="'CRITICAL', 'WARNING', or 'INFO'")
    message: str
    suggested_action: str


class ComplianceReport(BaseModel):
    status: str = Field(description="'COMPLIANT', 'FLAGGED_WARNING', or 'POLICY_VIOLATION'")
    risk_score: int = Field(description="Risk score from 0 (Clean) to 100 (High Risk)")
    summary: str
    violations: List[PolicyViolation] = Field(default_factory=list)
    auto_approvable: bool = False
    requires_vp_signoff: bool = False
    has_alcohol: bool = False
    policy_version: str = "2026.2"


# Cache of recently processed submissions for duplicate detection
# Key: hash string, Value: timestamp
recent_submissions_cache: Dict[str, Dict[str, Any]] = {}


class PolicyAuditorAgent:
    """Agent 2: Evaluates invoices against corporate compliance and expense policies."""

    def __init__(self, policy_path: Optional[Path] = None):
        self.policy_path = policy_path or (Path(__file__).resolve().parent.parent / "policies.json")
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        """Loads enterprise policy configuration."""
        try:
            if self.policy_path.exists():
                with open(self.policy_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load policy file: {e}")
        
        # Fallback default rules
        return {
            "company_name": "Acme Global Enterprise",
            "policy_version": "2026.2",
            "rules": {
                "meals_and_entertainment": {
                    "max_per_person_usd": settings.MAX_MEAL_LIMIT_PER_PERSON,
                    "alcohol_allowed": not settings.RESTRICT_ALCOHOL,
                    "weekend_meals_flag": True,
                },
                "software_and_saas": {
                    "max_direct_expense_usd": 500.00,
                },
                "general": {
                    "max_unapproved_transaction_usd": settings.MAX_UNAPPROVED_PURCHASE_AMOUNT,
                    "allowed_currencies": ["USD", "EUR", "GBP", "CAD", "MXN"],
                },
            },
        }

    def audit_invoice(self, invoice: ExtractedInvoice) -> ComplianceReport:
        """Audits an extracted invoice against company compliance rules."""
        violations: List[PolicyViolation] = []
        rules = self.policy.get("rules", {})
        risk_score = 0
        has_alcohol = False
        requires_vp = False

        # 1. Meal & Entertainment Rules
        if "meal" in invoice.category.lower() or "food" in invoice.category.lower() or "restaurant" in invoice.category.lower():
            meal_rules = rules.get("meals_and_entertainment", {})
            max_meal = meal_rules.get("max_per_person_usd", 75.00)
            
            if invoice.total_amount > max_meal:
                delta = invoice.total_amount - max_meal
                violations.append(
                    PolicyViolation(
                        rule_name="Meal Spending Limit Exceeded",
                        severity="WARNING",
                        message=f"Meal total (${invoice.total_amount:.2f}) exceeds the ${max_meal:.2f} single-person limit by ${delta:.2f}.",
                        suggested_action="Requires list of attendees or manager discretionary approval.",
                    )
                )
                risk_score += 25

            # Alcohol detection in line items
            alcohol_keywords = ["beer", "wine", "cocktail", "vodka", "liquor", "margarita", "cider", "alcohol", "tequila", "whiskey", "whisky"]
            found_alcohol_items = []
            for item in invoice.line_items:
                desc_lower = item.description.lower()
                is_alcohol = (item.category.lower() == "alcohol") or any(kw in desc_lower for kw in alcohol_keywords)
                if is_alcohol:
                    has_alcohol = True
                    found_alcohol_items.append(f"{item.description} (${item.total_price:.2f})")

            if has_alcohol and not meal_rules.get("alcohol_allowed", False):
                violations.append(
                    PolicyViolation(
                        rule_name="Restricted Item: Alcohol",
                        severity="CRITICAL",
                        message=f"Alcoholic beverages detected: {', '.join(found_alcohol_items)}. Corporate policy prohibits alcohol reimbursement without VP authorization.",
                        suggested_action="Deduct alcohol amount from total or escalate to Department VP.",
                    )
                )
                risk_score += 40

            # Weekend meal check
            try:
                dt = datetime.strptime(invoice.date, "%Y-%m-%d")
                if dt.weekday() in (5, 6) and meal_rules.get("weekend_meals_flag", True):
                    violations.append(
                        PolicyViolation(
                            rule_name="Weekend Transaction",
                            severity="INFO",
                            message=f"Transaction occurred on a weekend ({dt.strftime('%A')}).",
                            suggested_action="Confirm this was incurred during official business travel.",
                        )
                    )
                    risk_score += 10
            except Exception:
                pass

        # 2. Software & SaaS Rules
        if "software" in invoice.category.lower() or "saas" in invoice.category.lower() or "cloud" in invoice.category.lower():
            sw_rules = rules.get("software_and_saas", {})
            max_sw = sw_rules.get("max_direct_expense_usd", 500.00)
            if invoice.total_amount > max_sw:
                violations.append(
                    PolicyViolation(
                        rule_name="Software Direct Purchase Limit",
                        severity="WARNING",
                        message=f"Software expense (${invoice.total_amount:.2f}) exceeds the ${max_sw:.2f} direct expense threshold.",
                        suggested_action="IT Procurement review recommended to verify corporate licensing.",
                    )
                )
                risk_score += 20

        # 3. General Spending Limit Check
        gen_rules = rules.get("general", {})
        max_trans = gen_rules.get("max_unapproved_transaction_usd", 1000.00)
        if invoice.total_amount > max_trans:
            requires_vp = True
            violations.append(
                PolicyViolation(
                    rule_name="High-Value Expenditure",
                    severity="CRITICAL",
                    message=f"Expense of ${invoice.total_amount:,.2f} exceeds the ${max_trans:,.2f} single-transaction threshold.",
                    suggested_action="Requires VP sign-off and Purchase Order reference.",
                )
            )
            risk_score += 35

        # 4. Duplicate Detection Check
        duplicate_key = f"{invoice.vendor_name.lower().strip()}_{invoice.date}_{invoice.total_amount}"
        if duplicate_key in recent_submissions_cache:
            prev_entry = recent_submissions_cache[duplicate_key]
            violations.append(
                PolicyViolation(
                    rule_name="Potential Duplicate Submission",
                    severity="CRITICAL",
                    message=f"An identical invoice ({invoice.vendor_name} for ${invoice.total_amount:.2f} on {invoice.date}) was previously submitted on {prev_entry.get('submitted_at')}.",
                    suggested_action="Verify this is not a duplicate reimbursement request.",
                )
            )
            risk_score += 50
        else:
            recent_submissions_cache[duplicate_key] = {
                "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "vendor": invoice.vendor_name,
                "amount": invoice.total_amount,
            }

        # Determine overall status
        risk_score = min(risk_score, 100)
        has_critical = any(v.severity == "CRITICAL" for v in violations)
        has_warning = any(v.severity == "WARNING" for v in violations)

        if has_critical:
            status = "POLICY_VIOLATION"
            summary = f"🔴 {len(violations)} Policy Violations Detected (Risk Score: {risk_score}/100)"
        elif has_warning or len(violations) > 0:
            status = "FLAGGED_WARNING"
            summary = f"🟡 {len(violations)} Policy Warnings to Review (Risk Score: {risk_score}/100)"
        else:
            status = "COMPLIANT"
            summary = "🟢 100% Compliant with Corporate Expense Policy"

        auto_approvable = (status == "COMPLIANT" and invoice.total_amount <= 250.00)

        return ComplianceReport(
            status=status,
            risk_score=risk_score,
            summary=summary,
            violations=violations,
            auto_approvable=auto_approvable,
            requires_vp_signoff=requires_vp,
            has_alcohol=has_alcohol,
            policy_version=self.policy.get("policy_version", "2026.2"),
        )
