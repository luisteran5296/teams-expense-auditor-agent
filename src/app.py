import sys
from pathlib import Path

# Add project root directory to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import logging
from typing import Optional
from fastapi import FastAPI, Request, Response, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
)
from botbuilder.schema import Activity

from src.config import settings
from src.agents.approval import ApprovalOrchestrator
from src.teams.bot import ExpenseAuditorTeamsBot

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("teams-expense-auditor-agent")

app = FastAPI(
    title="Multi-Agent Invoice & Expense Auditor for Microsoft Teams",
    description="Multimodal Vision receipt extraction, corporate policy compliance auditing, and Human-in-the-Loop manager approvals.",
    version="1.0.0",
)

# Mount generated ledgers and samples for direct downloads
app.mount("/ledgers", StaticFiles(directory=str(settings.LEDGERS_DIR)), name="ledgers")
app.mount("/samples", StaticFiles(directory=str(settings.SAMPLES_DIR)), name="samples")

# Initialize orchestrator and bot
orchestrator = ApprovalOrchestrator()
bot = ExpenseAuditorTeamsBot(orchestrator=orchestrator)

# Bot Framework Adapter
adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.BOT_ID or "",
    app_password=settings.BOT_PASSWORD or "",
    channel_auth_tenant=settings.BOT_TENANT_ID or None,
)
adapter = BotFrameworkAdapter(adapter_settings)


async def on_adapter_error(context: TurnContext, error: Exception):
    logger.error(f"[on_turn_error] Unhandled error: {error}", exc_info=True)
    await context.send_activity("⚠️ Sorry, an unexpected error occurred while processing your expense document.")


adapter.on_turn_error = on_adapter_error


@app.get("/")
async def root():
    """Service status and diagnostic overview."""
    stats = orchestrator.ledger.get_summary_statistics()
    return {
        "service": "Multi-Agent Invoice & Expense Auditor for Microsoft Teams",
        "status": "online",
        "gemini_configured": orchestrator.extractor.is_configured,
        "bot_configured": bool(settings.BOT_ID and settings.BOT_PASSWORD),
        "ledger_stats": stats,
        "endpoints": {
            "teams_webhook": "/api/messages",
            "audit_upload": "/api/audit",
            "audit_ledger": "/ledgers/expense_audit_ledger.xlsx",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint for container monitoring."""
    return {
        "status": "healthy",
        "gemini_model": settings.GEMINI_MODEL,
        "policy_version": orchestrator.auditor.policy.get("policy_version", "2026.2"),
    }


@app.post("/api/audit")
async def direct_audit(
    file: UploadFile = File(...),
    submitter: str = Form("Employee"),
):
    """
    Direct HTTP endpoint to audit an invoice or receipt image without Teams.
    """
    file_bytes = await file.read()
    mime_type = file.content_type or "image/png"

    result = await orchestrator.audit_submitted_document(
        file_data=file_bytes,
        mime_type=mime_type,
        submitter=submitter,
    )

    return {
        "submission_id": result["submission_id"],
        "submitter": submitter,
        "invoice": result["invoice"].model_dump(),
        "compliance": result["compliance"].model_dump(),
        "status": result["status"],
    }


@app.post("/api/messages")
async def messages(request: Request) -> Response:
    """
    Main webhook endpoint for Microsoft Teams and Bot Framework activities.
    """
    content_type = request.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return Response(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    async def turn_call(turn_context: TurnContext):
        await bot.on_turn(turn_context)

    try:
        invoke_response = await adapter.process_activity(activity, auth_header, turn_call)
        if invoke_response:
            return JSONResponse(
                status_code=invoke_response.status,
                content=invoke_response.body,
            )
        return Response(status_code=status.HTTP_201_CREATED)

    except Exception as ex:
        logger.error(f"Error handling Bot Framework activity: {ex}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(ex)},
        )


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Teams Expense Auditor Agent on port {settings.PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
