"""
Twilio WhatsApp integration service.

Responsibilities:
  - Validate incoming Twilio webhook signatures
  - Parse WhatsApp message payloads
  - Upsert Citizens from WhatsApp sender info
  - Persist Messages to the database
  - Broadcast new messages to WebSocket dashboard consumers
  - Trigger async AI insight generation via Celery
"""

import logging
from typing import Optional
from django.conf import settings
from twilio.request_validator import RequestValidator
from twilio.rest import Client as TwilioRestClient
from messages_app.models import Citizen, Message
from projects.models import AnalysisProject

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signature Validation
# ---------------------------------------------------------------------------

def validate_twilio_signature(request) -> bool:
    """
    Verify that the incoming webhook request genuinely comes from Twilio.

    Twilio signs every webhook with an HMAC-SHA1 signature using your
    Auth Token. We must validate this before processing any payload.

    Args:
        request: Django HttpRequest from the webhook view.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)

    # Build the full URL Twilio signed (must match exactly what Twilio sees)
    url = request.build_absolute_uri()

    # Twilio sends POST params as the signed payload
    post_params = request.POST.dict()

    signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")

    is_valid = validator.validate(url, post_params, signature)

    if not is_valid:
        logger.warning("Invalid Twilio signature from IP: %s", request.META.get("REMOTE_ADDR"))

    return is_valid


# ---------------------------------------------------------------------------
# Payload Parsing
# ---------------------------------------------------------------------------

def parse_whatsapp_payload(post_data: dict) -> dict:
    """
    Extract relevant fields from a Twilio WhatsApp webhook POST payload.

    Twilio WhatsApp payload fields we care about:
      - From:          Sender's WhatsApp number e.g. "whatsapp:+254712345678"
      - Body:          Message text content
      - ProfileName:   WhatsApp display name of the sender
      - WaId:          WhatsApp ID (numeric phone without prefix)
      - MessageSid:    Unique Twilio message identifier
      - NumMedia:      Number of media attachments (0 for text)

    Args:
        post_data: request.POST dict from Django view.

    Returns:
        dict with normalized fields.
    """
    raw_from = post_data.get("From", "")            
    phone_number = raw_from.replace("whatsapp:", "").strip() 

    return {
        "phone_number": phone_number,
        "profile_name": post_data.get("ProfileName", "").strip() or None,
        "wa_id": post_data.get("WaId", "").strip(),
        "body": post_data.get("Body", "").strip(),
        "message_sid": post_data.get("MessageSid", ""),
        "num_media": int(post_data.get("NumMedia", 0)),
    }


# ---------------------------------------------------------------------------
# Citizen Resolution
# ---------------------------------------------------------------------------

def get_or_create_citizen(phone_number: str, profile_name: Optional[str] = None) -> Citizen:
    """
    Find or create a Citizen record based on the WhatsApp phone number.

    If the citizen exists but has no name and a name is now available,
    we update it (Twilio sometimes provides the WhatsApp display name).

    Args:
        phone_number: E.164 formatted phone number.
        profile_name: Optional WhatsApp display name.

    Returns:
        Citizen instance.
    """
    citizen, created = Citizen.objects.get_or_create(
        phone_number=phone_number,
        defaults={"name": profile_name},
    )

    if not created and profile_name and not citizen.name:
        citizen.name = profile_name
        citizen.save(update_fields=["name"])

    if created:
        logger.info("New citizen registered: %s (%s)", phone_number, profile_name)

    return citizen


# ---------------------------------------------------------------------------
# Message Persistence
# ---------------------------------------------------------------------------

def ingest_whatsapp_message(
    project: AnalysisProject,
    citizen: Citizen,
    body: str,
    message_sid: str,
) -> Optional[Message]:
    """
    Persist an incoming WhatsApp message.

    Idempotent: uses message_sid stored in metadata to avoid duplicates
    (Twilio can retry webhooks on failure).

    Args:
        project:     The AnalysisProject this message belongs to.
        citizen:     The resolved Citizen sender.
        body:        The text content of the message.
        message_sid: Twilio MessageSid (used for dedup).

    Returns:
        Message instance if created, None if duplicate.
    """
    from django.utils import timezone

    # Deduplicate using external_id field on Message
    if Message.objects.filter(external_id=message_sid).exists():
        logger.info("Duplicate webhook ignored for MessageSid: %s", message_sid)
        return None

    message = Message.objects.create(
        project=project,
        citizen=citizen,
        content=body,
        source=Message.Source.WHATSAPP,
        timestamp=timezone.now(),
        external_id=message_sid,
    )

    logger.info(
        "WhatsApp message ingested [project=%s, citizen=%s, sid=%s]",
        project.pk,
        citizen.phone_number,
        message_sid,
    )

    return message


# ---------------------------------------------------------------------------
# Twilio Reply (Optional immediate acknowledgement)
# ---------------------------------------------------------------------------

def send_whatsapp_acknowledgement(to_number: str, body: str) -> None:
    """
    Send an immediate WhatsApp acknowledgement to the citizen via Twilio.

    This is separate from the AI-generated draft response flow. Use this
    for instant "Thank you, we received your feedback" messages.

    Args:
        to_number: Recipient phone in E.164 format e.g. "+254712345678"
        body:      Message text to send.
    """
    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to_number}",
            body=body,
        )
        logger.info("Acknowledgement sent to %s", to_number)
    except Exception as exc:
        # Non-fatal: log and continue — don't break the ingestion flow
        logger.error("Failed to send acknowledgement to %s: %s", to_number, exc)