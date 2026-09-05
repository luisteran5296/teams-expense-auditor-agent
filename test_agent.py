import sys
import os
import asyncio
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Ensure UTF-8 stdout on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from src.agents.extractor import DocumentExtractorAgent
from src.agents.auditor import PolicyAuditorAgent
from src.agents.approval import ApprovalOrchestrator
from src.ledger.manager import LedgerManager


async def run_diagnostics():
    print("=" * 65)
    print("🚀 Multi-Agent Invoice & Expense Auditor - Test Suite")
    print("=" * 65)

    samples_dir = _PROJECT_ROOT / "samples"
    software_inv_path = samples_dir / "sample_compliant_software_invoice.png"
    dining_receipt_path = samples_dir / "sample_flagged_dining_receipt.png"

    assert software_inv_path.exists(), f"Sample file {software_inv_path} missing!"
    assert dining_receipt_path.exists(), f"Sample file {dining_receipt_path} missing!"

    orchestrator = ApprovalOrchestrator()

    # --- Test 1: Compliant Software Invoice ---
    print("\n[Test 1] Ingesting Compliant Software Invoice...")
    print(f"  * File: {software_inv_path.name}")
    res_compliant = await orchestrator.audit_submitted_document(
        file_data=software_inv_path,
        mime_type="image/png",
        submitter="Sarah Connor (Engineering)",
    )

    inv_c = res_compliant["invoice"]
    comp_c = res_compliant["compliance"]
    sub_c_id = res_compliant["submission_id"]

    print(f"  * Extracted Vendor: {inv_c.vendor_name}")
    print(f"  * Date: {inv_c.date} | Category: {inv_c.category}")
    print(f"  * Total: ${inv_c.total_amount:.2f} {inv_c.currency}")
    print(f"  * Line Items: {len(inv_c.line_items)} extracted")
    for it in inv_c.line_items:
        print(f"    - {it.description}: ${it.total_price:.2f}")

    print(f"  * Compliance Status: {comp_c.status} (Risk: {comp_c.risk_score}/100)")
    print(f"  * Summary: {comp_c.summary}")
    assert comp_c.status == "COMPLIANT", f"Expected COMPLIANT but got {comp_c.status}"

    # --- Test 2: Flagged Dining Receipt with Alcohol ---
    print("\n[Test 2] Ingesting Dining Receipt with Policy Flags...")
    print(f"  * File: {dining_receipt_path.name}")
    res_flagged = await orchestrator.audit_submitted_document(
        file_data=dining_receipt_path,
        mime_type="image/png",
        submitter="John Smith (Sales)",
    )

    inv_f = res_flagged["invoice"]
    comp_f = res_flagged["compliance"]

    print(f"  * Extracted Vendor: {inv_f.vendor_name}")
    print(f"  * Total: ${inv_f.total_amount:.2f}")
    print(f"  * Compliance Status: {comp_f.status} (Risk: {comp_f.risk_score}/100)")
    print(f"  * Summary: {comp_f.summary}")
    print(f"  * Detected Violations ({len(comp_f.violations)}):")
    for v in comp_f.violations:
        print(f"    - [{v.severity}] {v.rule_name}: {v.message}")

    assert comp_f.status in ("POLICY_VIOLATION", "FLAGGED_WARNING"), "Expected policy flag!"

    # --- Test 3: Manager Approval & Excel Ledger Update ---
    print("\n[Test 3] Simulating Human-in-the-Loop Manager Decision...")
    print(f"  * Manager approving submission: {sub_c_id}")
    decision_result = orchestrator.apply_decision(
        submission_id=sub_c_id,
        decision="APPROVED",
        approver="Alex Rodriguez (Engineering Director)",
        notes="Pre-approved monthly cloud subscription.",
    )

    print(f"  * Decision Recorded: {decision_result.get('decision')}")
    print(f"  * Assigned Transaction ID: {decision_result.get('transaction_id')}")
    print(f"  * Download URL: {decision_result.get('ledger_download_url')}")
    assert decision_result.get("success") is True, "Decision failed!"

    # --- Test 4: Verify Excel Ledger Statistics ---
    print("\n[Test 4] Verifying Corporate Audit Ledger Excel File...")
    ledger = LedgerManager()
    stats = ledger.get_summary_statistics()
    print(f"  * Total Logged Records: {stats.get('total_records')}")
    print(f"  * Total Approved Spend: ${stats.get('total_approved_spend_usd'):,.2f}")
    print(f"  * Approved Count: {stats.get('approved_count')}")
    assert stats.get("total_records") >= 1, "Ledger has no records!"

    print("\n" + "=" * 65)
    print("✅ All Multi-Agent Expense Auditor diagnostic checks PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
