"""PDF/image handling for multimodal Claude content blocks."""

import base64
import aiohttp
import structlog
from typing import Any

log = structlog.get_logger(__name__)

SUPPORTED_IMAGE_TYPES = {"png", "jpg", "jpeg", "gif", "webp"}
SUPPORTED_DOC_TYPES = {"pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


async def process_attachments(attachments: list[Any]) -> list[dict[str, Any]]:
    """Process Discord attachments into Claude content blocks.

    Args:
        attachments: List of discord.Attachment objects.

    Returns:
        List of content blocks for the Claude API.
    """
    content_blocks: list[dict[str, Any]] = []

    for attachment in attachments:
        if attachment.size > MAX_FILE_SIZE:
            log.warning("attachment_too_large", filename=attachment.filename, size=attachment.size)
            content_blocks.append({
                "type": "text",
                "text": f"[File '{attachment.filename}' is too large to process ({attachment.size / 1024 / 1024:.1f}MB)]",
            })
            continue

        ext = attachment.filename.rsplit(".", 1)[-1].lower() if "." in attachment.filename else ""

        if ext in SUPPORTED_IMAGE_TYPES:
            content_blocks.extend(await _process_image(attachment, ext))
        elif ext in SUPPORTED_DOC_TYPES:
            content_blocks.extend(await _process_pdf(attachment))
        else:
            content_blocks.append({
                "type": "text",
                "text": f"[Unsupported file type: {attachment.filename}]",
            })

    return content_blocks


async def _process_image(attachment: Any, ext: str) -> list[dict[str, Any]]:
    """Download and encode an image attachment."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    return [{"type": "text", "text": f"[Failed to download image: {attachment.filename}]"}]
                data = await resp.read()

        media_type = f"image/{ext}"
        if ext == "jpg":
            media_type = "image/jpeg"

        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(data).decode("utf-8"),
                },
            },
            {
                "type": "text",
                "text": f"[Uploaded image: {attachment.filename}]",
            },
        ]
    except Exception as e:
        log.error("image_process_error", filename=attachment.filename, error=str(e))
        return [{"type": "text", "text": f"[Error processing image: {attachment.filename}]"}]


async def _process_pdf(attachment: Any) -> list[dict[str, Any]]:
    """Download and encode a PDF attachment."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    return [{"type": "text", "text": f"[Failed to download PDF: {attachment.filename}]"}]
                data = await resp.read()

        return [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.b64encode(data).decode("utf-8"),
                },
            },
            {
                "type": "text",
                "text": f"[Uploaded PDF: {attachment.filename}] — Please analyze this document.",
            },
        ]
    except Exception as e:
        log.error("pdf_process_error", filename=attachment.filename, error=str(e))
        return [{"type": "text", "text": f"[Error processing PDF: {attachment.filename}]"}]
