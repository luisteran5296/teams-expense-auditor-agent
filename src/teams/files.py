import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class TeamsFileManager:
    """Helper to download user uploaded receipt and invoice images or PDFs."""

    @staticmethod
    async def download_attachment(
        content_url: str,
        auth_token: Optional[str] = None,
    ) -> Optional[bytes]:
        """Downloads file content bytes from Teams attachment URL."""
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(content_url, headers=headers)
                if resp.status_code == 200:
                    return resp.content
                else:
                    logger.warning(
                        f"Failed to download attachment from {content_url}: HTTP {resp.status_code}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error downloading Teams attachment: {e}", exc_info=True)
            return None
