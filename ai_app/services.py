import logging
from django.utils import timezone
from .models import AIDraft, OutgoingMessage
from messages_app.models import Message
from projects.models import AnalysisProject
from ai_services.gemini_client import GeminiClient, GeminiClientError
from ai_services.prompt_builder import build_draft_response_prompt, SYSTEM_BASE

logger = logging.getLogger(__name__)


def generate_draft_for_message(message: Message, project: AnalysisProject) -> AIDraft:
    """
    Generate an AI draft response for a single citizen message.

    AI logic is fully decoupled from the view layer.
    """
    prompt = build_draft_response_prompt(message.content, project.name)

    try:
        generated_text = GeminiClient.generate(prompt, system_instruction=SYSTEM_BASE)
    except GeminiClientError as e:
        logger.error("Draft generation failed for message %s: %s", message.pk, e)
        raise

    draft = AIDraft.objects.create(
        project=project,
        message=message,
        generated_text=generated_text,
        status=AIDraft.Status.PENDING,
    )
    return draft


def approve_and_send_draft(draft: AIDraft) -> OutgoingMessage:
    """
    Approve a draft and create an outgoing message record.
    In production, this would trigger an SMS/email gateway.
    """
    text_to_send = draft.edited_text or draft.generated_text

    draft.status = AIDraft.Status.SENT
    draft.save(update_fields=["status"])

    outgoing = OutgoingMessage.objects.create(
        citizen=draft.message.citizen,
        draft=draft,
        sent_text=text_to_send,
        status=OutgoingMessage.Status.SENT,
        sent_at=timezone.now(),
    )
    return outgoing


def update_draft(draft: AIDraft, edited_text: str) -> AIDraft:
    draft.edited_text = edited_text
    draft.save(update_fields=["edited_text"])
    return draft