"""
Celery async tasks for post-ingestion processing.

Why async?
  Twilio expects a webhook response within 15 seconds or it retries.
  AI insight generation can take 5–30 seconds for large message sets.
  We respond to Twilio immediately, then process in the background.
"""

import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="twilio_app.broadcast_new_message",
)
def broadcast_new_message_task(self, message_id: int, project_id: int) -> None:
    """
    Broadcast a newly ingested WhatsApp message to all dashboard WebSocket
    clients subscribed to the project's channel group.

    This task runs immediately after message ingestion so the frontend
    dashboard updates in real-time without polling.

    Args:
        message_id: PK of the newly created Message.
        project_id: PK of the AnalysisProject it belongs to.
    """
    try:
        from messages_app.models import Message
        from twilio_app.serializers import WhatsAppMessageSerializer

        message = Message.objects.select_related("citizen").get(pk=message_id)
        serialized = WhatsAppMessageSerializer(message).data

        channel_layer = get_channel_layer()
        group_name = f"project_{project_id}_messages"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "new_message",      # maps to consumer method new_message()
                "message": serialized,
            },
        )
        logger.info(
            "Broadcast new message #%s to WebSocket group %s", message_id, group_name
        )
    except Exception as exc:
        logger.exception("broadcast_new_message_task failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,  # wait 60s before retry
    name="twilio_app.trigger_insight_generation",
)
def trigger_insight_generation_task(self, project_id: int) -> None:
    from django.conf import settings
    from django.core.cache import cache  # ← add cache check
    from projects.models import AnalysisProject
    from messages_app.models import Message
    from insights.services import generate_insights_for_project
    from twilio_app.serializers import InsightBroadcastSerializer
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    INSIGHT_TRIGGER_THRESHOLD = getattr(settings, "INSIGHT_TRIGGER_EVERY_N_MESSAGES", 10)

    # ── Guard: prevent duplicate runs within 5 minutes ──────────────────
    lock_key = f"insight_lock_{project_id}"
    if cache.get(lock_key):
        logger.info("Insight generation already ran recently for project %s, skipping", project_id)
        return
    cache.set(lock_key, True, timeout=300)  # lock for 5 minutes

    try:
        project = AnalysisProject.objects.get(pk=project_id)
        total = Message.objects.filter(project=project).count()

        if total % INSIGHT_TRIGGER_THRESHOLD != 0:
            logger.debug(
                "Insight threshold not reached for project %s (%d messages)", project_id, total
            )
            cache.delete(lock_key)  # release lock early
            return

        logger.info("Triggering insight generation for project %s (%d messages)", project_id, total)
        insights = generate_insights_for_project(project)

        channel_layer = get_channel_layer()
        group_name = f"project_{project_id}_insights"
        serialized = InsightBroadcastSerializer(insights, many=True).data

        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "new_insights", "insights": serialized},
        )
        logger.info("Broadcast %d insights to WebSocket group %s", len(insights), group_name)

    except AnalysisProject.DoesNotExist:
        logger.error("Project %s not found for insight generation", project_id)
    except Exception as exc:
        logger.exception("trigger_insight_generation_task failed: %s", exc)
        raise self.retry(exc=exc)