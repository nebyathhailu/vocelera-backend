import logging
from django.utils import timezone
from django.conf import settings
from .models import AIDraft, OutgoingMessage
from messages_app.models import Message
from projects.models import AnalysisProject
from insights.models import Insight
from ai_services.gemini_client import GeminiClient, GeminiClientError
from ai_services.prompt_builder import build_draft_response_prompt, SYSTEM_BASE

logger = logging.getLogger(__name__)


# ─── Twilio delivery ──────────────────────────────────────────────────────────

def _deliver_via_twilio(to_number: str, body: str) -> bool:
    """
    Actually send a WhatsApp message via Twilio.

    Args:
        to_number: E.164 phone number e.g. "+254712345678"
        body:      Message text to send

    Returns:
        bool: True if delivered successfully, False otherwise.
    """
    try:
        from twilio.rest import Client as TwilioClient
        from twilio.base.exceptions import TwilioRestException

        client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )

        # Ensure the number has whatsapp: prefix
        to_whatsapp = (
            f"whatsapp:{to_number}"
            if not to_number.startswith("whatsapp:")
            else to_number
        )

        message = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to_whatsapp,
            body=body,
        )

        logger.info(
            "Twilio delivery success [to=%s, sid=%s, status=%s]",
            to_number, message.sid, message.status,
        )
        return True

    except TwilioRestException as exc:
        logger.error(
            "Twilio delivery failed [to=%s, code=%s, msg=%s]",
            to_number, exc.code, exc.msg,
        )
        return False
    except Exception as exc:
        logger.exception("Unexpected Twilio error [to=%s]: %s", to_number, exc)
        return False


# ─── Single draft generation ──────────────────────────────────────────────────

def generate_draft_for_message(
    message: Message,
    project: AnalysisProject,
) -> AIDraft:
    """
    Generate an AI draft response for a single citizen message.
    Pulls live insight context from the project to enrich the prompt.
    """
    # Pull top insights for richer prompt context
    insights_context = list(
        Insight.objects.filter(project=project)
        .order_by("-priority_score")
        .values("theme", "sentiment", "priority_score")[:5]
    )

    citizen_name = message.citizen.name or "" if message.citizen else ""

    prompt = build_draft_response_prompt(
        citizen_message  = message.content,
        project_name     = project.name,
        citizen_name     = citizen_name,
        insights_context = insights_context,
    )

    try:
        generated_text = GeminiClient.generate(
            prompt, system_instruction=SYSTEM_BASE
        )
    except GeminiClientError as e:
        logger.error(
            "Draft generation failed for message %s: %s", message.pk, e
        )
        raise

    draft = AIDraft.objects.create(
        project        = project,
        message        = message,
        generated_text = generated_text,
        status         = AIDraft.Status.PENDING,
    )
    return draft


# ─── Bulk draft generation ────────────────────────────────────────────────────

def generate_drafts_for_all_messages(project: AnalysisProject) -> dict:
    """
    Generate AI response drafts for every citizen message in a project
    that does not already have a draft.

    Returns:
        dict: { "created": int, "skipped": int, "failed": int, "drafts": [AIDraft] }
    """
    messages = Message.objects.filter(
        project=project
    ).select_related("citizen")

    # Find message IDs that already have a draft
    existing_draft_message_ids = set(
        AIDraft.objects.filter(project=project)
        .values_list("message_id", flat=True)
    )

    # Pull insights once for all prompts
    insights_context = list(
        Insight.objects.filter(project=project)
        .order_by("-priority_score")
        .values("theme", "sentiment", "priority_score")[:5]
    )

    created, skipped, failed = 0, 0, 0
    drafts = []

    for message in messages:
        if message.id in existing_draft_message_ids:
            skipped += 1
            continue

        try:
            citizen_name = message.citizen.name or "" if message.citizen else ""

            prompt = build_draft_response_prompt(
                citizen_message  = message.content,
                project_name     = project.name,
                citizen_name     = citizen_name,
                insights_context = insights_context,
            )

            generated_text = GeminiClient.generate(
                prompt, system_instruction=SYSTEM_BASE
            )

            draft = AIDraft.objects.create(
                project        = project,
                message        = message,
                generated_text = generated_text,
                status         = AIDraft.Status.PENDING,
            )
            drafts.append(draft)
            created += 1

        except Exception as exc:
            logger.error(
                "Failed to generate draft for message #%s: %s",
                message.pk, exc
            )
            failed += 1
            continue

    logger.info(
        "Bulk draft generation complete [project=%s, created=%d, skipped=%d, failed=%d]",
        project.pk, created, skipped, failed,
    )
    return {
        "created": created,
        "skipped": skipped,
        "failed":  failed,
        "drafts":  drafts,
    }


# ─── Approve and actually send via Twilio ────────────────────────────────────

def approve_and_send_draft(draft: AIDraft) -> OutgoingMessage:
    """
    Approve a draft, deliver it via Twilio WhatsApp, and record the result.

    Flow:
        1. Determine the text to send (edited > generated)
        2. Get the citizen's phone number from the linked message
        3. Call Twilio API to actually deliver the message
        4. Update draft status
        5. Create OutgoingMessage record with delivery status
    """
    text_to_send = draft.edited_text.strip() if draft.edited_text.strip() else draft.generated_text

    # Get phone number from the linked citizen
    message  = draft.message if isinstance(draft.message, Message) else \
               Message.objects.select_related("citizen").get(pk=draft.message_id)
    citizen  = message.citizen
    phone    = citizen.phone_number if citizen else None

    delivery_status = OutgoingMessage.Status.FAILED

    if not phone:
        logger.warning(
            "Draft #%s has no citizen phone number — skipping Twilio delivery",
            draft.pk
        )
    else:
        delivered = _deliver_via_twilio(to_number=phone, body=text_to_send)
        delivery_status = (
            OutgoingMessage.Status.SENT if delivered
            else OutgoingMessage.Status.FAILED
        )

    # Update draft status
    draft.status = AIDraft.Status.SENT
    draft.save(update_fields=["status"])

    # Record outgoing message with real delivery status
    outgoing = OutgoingMessage.objects.create(
        citizen   = citizen,
        draft     = draft,
        sent_text = text_to_send,
        status    = delivery_status,
        sent_at   = timezone.now() if delivery_status == OutgoingMessage.Status.SENT else None,
    )

    logger.info(
        "Draft #%s approved [delivery=%s, to=%s]",
        draft.pk, delivery_status, phone,
    )
    return outgoing


# ─── Bulk approve and send ────────────────────────────────────────────────────

def approve_and_send_all_pending(project: AnalysisProject) -> dict:
    """
    Approve and send every pending draft for a project in one call.

    Returns:
        dict: { "sent": int, "failed": int }
    """
    pending_drafts = AIDraft.objects.filter(
        project = project,
        status  = AIDraft.Status.PENDING,
    ).select_related("message__citizen")

    sent, failed = 0, 0

    for draft in pending_drafts:
        try:
            result = approve_and_send_draft(draft)
            if result.status == OutgoingMessage.Status.SENT:
                sent += 1
            else:
                failed += 1
        except Exception as exc:
            logger.error("Failed to send draft #%s: %s", draft.pk, exc)
            failed += 1

    return {"sent": sent, "failed": failed}


# ─── Edit draft ───────────────────────────────────────────────────────────────

def update_draft(draft: AIDraft, edited_text: str) -> AIDraft:
    draft.edited_text = edited_text
    draft.save(update_fields=["edited_text"])
    return draft