import logging
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.shortcuts import get_object_or_404
from twilio.twiml.messaging_response import MessagingResponse
from projects.models import AnalysisProject
from .services import (
    validate_twilio_signature,
    parse_whatsapp_payload,
    get_or_create_citizen,
    ingest_whatsapp_message,
    send_whatsapp_acknowledgement,
)
from .tasks import broadcast_new_message_task, trigger_insight_generation_task

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):

    def post(self, request, project_id: int):
        # Step 1: Validate Twilio signature (skipped in DEBUG mode)
        if not settings.DEBUG and not validate_twilio_signature(request):
            logger.warning("Rejected: invalid Twilio signature from %s", request.META.get("REMOTE_ADDR"))
            return HttpResponse("Forbidden", status=403)

        # Step 2: Resolve project
        project = get_object_or_404(AnalysisProject, pk=project_id)

        # Step 3: Parse payload
        payload = parse_whatsapp_payload(request.POST)
        if not payload["body"]:
            return self._twiml_response()

        # Step 4: Resolve citizen
        citizen = get_or_create_citizen(
            phone_number = payload["phone_number"],
            profile_name = payload["profile_name"],
        )

        # Step 5: Ingest message (idempotent via external_id/MessageSid)
        message = ingest_whatsapp_message(
            project     = project,
            citizen     = citizen,
            body        = payload["body"],
            message_sid = payload["message_sid"],
        )

        if message is None:
            # Duplicate webhook retry — respond 200 so Twilio stops retrying
            return self._twiml_response()

        # Step 6: Fire async tasks
        # Real-time broadcast to dashboard WebSocket clients
        broadcast_new_message_task.delay(
            message_id = message.pk,
            project_id = project.pk,
        )
        # AI insight generation (every N messages, throttled inside task)
        trigger_insight_generation_task.delay(project_id=project.pk)

        # Step 7: Instant acknowledgement to citizen via Twilio API
        send_whatsapp_acknowledgement(
            to_number = payload["phone_number"],
            body = (
                "Thank you for your feedback! Your message has been received "
            ),
        )

        return self._twiml_response()

    @staticmethod
    def _twiml_response() -> HttpResponse:
        """Return an empty TwiML 200 response to satisfy Twilio."""
        return HttpResponse(
            str(MessagingResponse()),
            content_type="application/xml",
            status=200,
        )