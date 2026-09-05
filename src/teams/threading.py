import logging
from botbuilder.schema import Activity

logger = logging.getLogger(__name__)


def apply_threading(incoming_activity: Activity, reply_activity: Activity) -> Activity:
    """
    Applies threading rules from DEM334.
    If the conversation is in a channel or group chat, sets reply_to_id
    to ensure the bot's response remains inside the message thread.
    """
    conv_type = getattr(incoming_activity.conversation, "conversation_type", None)
    if conv_type == "channel" or (
        incoming_activity.conversation and incoming_activity.conversation.is_group
    ):
        reply_activity.reply_to_id = incoming_activity.id
        logger.debug(f"Applied threading reply_to_id={incoming_activity.id} for {conv_type}")

    return reply_activity
