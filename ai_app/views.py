import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from messages_app.models import Message
from projects.models import AnalysisProject
from .models import AIDraft
from .serializers import AIDraftSerializer, OutgoingMessageSerializer
from . import services

logger = logging.getLogger(__name__)


class AIDraftViewSet(viewsets.ModelViewSet):
    serializer_class = AIDraftSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        qs = AIDraft.objects.select_related("message__citizen", "project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.order_by("-created_at")

    # ── Single draft generation ───────────────────────────────────────────────
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """
        Generate a draft for ONE message.

        Body: { "message_id": 5, "project_id": 1 }
        """
        message_id = request.data.get("message_id")
        project_id = request.data.get("project_id")
        message    = get_object_or_404(Message, pk=message_id)
        project    = get_object_or_404(AnalysisProject, pk=project_id)

        try:
            draft = services.generate_draft_for_message(message, project)
        except Exception as e:
            return Response(
                {"error": "Draft generation failed.", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            AIDraftSerializer(draft).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Bulk draft generation ─────────────────────────────────────────────────
    @action(detail=False, methods=["post"], url_path="generate-all")
    def generate_all(self, request):
        """
        Generate drafts for ALL messages in a project that don't have one yet.

        Body: { "project_id": 1 }

        Response:
        {
          "created": 12,
          "skipped": 3,
          "failed": 0,
          "drafts": [ ...AIDraft objects... ]
        }
        """
        project = get_object_or_404(
            AnalysisProject, pk=request.data.get("project_id")
        )
        try:
            result = services.generate_drafts_for_all_messages(project)
        except Exception as e:
            return Response(
                {"error": "Bulk generation failed.", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({
            "created": result["created"],
            "skipped": result["skipped"],
            "failed":  result["failed"],
            "drafts":  AIDraftSerializer(result["drafts"], many=True).data,
        }, status=status.HTTP_201_CREATED)

    # ── Edit draft ────────────────────────────────────────────────────────────
    @action(detail=True, methods=["patch"], url_path="edit")
    def edit(self, request, pk=None):
        draft = self.get_object()
        edited_text = request.data.get("edited_text", "")
        draft = services.update_draft(draft, edited_text)
        return Response(AIDraftSerializer(draft).data)

    # ── Approve and send ONE draft via Twilio ─────────────────────────────────
    @action(detail=True, methods=["post"], url_path="approve-and-send")
    def approve_and_send(self, request, pk=None):
        """
        Approve a single draft and deliver it to the citizen via Twilio WhatsApp.

        Response includes delivery status so the frontend can show
        whether the message actually reached WhatsApp.
        """
        draft = self.get_object()

        if draft.status == AIDraft.Status.SENT:
            return Response(
                {"error": "This draft has already been sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            outgoing = services.approve_and_send_draft(draft)
        except Exception as e:
            logger.exception("approve_and_send failed for draft #%s", pk)
            return Response(
                {"error": "Delivery failed.", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "draft":    AIDraftSerializer(draft).data,
            "outgoing": OutgoingMessageSerializer(outgoing).data,
            "delivered": outgoing.status == "sent",
        })

    # ── Bulk approve and send all pending drafts ──────────────────────────────
    @action(detail=False, methods=["post"], url_path="send-all")
    def send_all(self, request):
        """
        Approve and send every pending draft for a project via Twilio.

        Body: { "project_id": 1 }

        Response: { "sent": 10, "failed": 2 }
        """
        project = get_object_or_404(
            AnalysisProject, pk=request.data.get("project_id")
        )
        result = services.approve_and_send_all_pending(project)
        return Response(result)