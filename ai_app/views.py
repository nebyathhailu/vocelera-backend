from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from messages_app.models import Message
from projects.models import AnalysisProject
from .models import AIDraft
from .serializers import AIDraftSerializer, OutgoingMessageSerializer
from . import services


class AIDraftViewSet(viewsets.ModelViewSet):
    serializer_class = AIDraftSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        qs = AIDraft.objects.select_related("message", "project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        message_id = request.data.get("message_id")
        project_id = request.data.get("project_id")
        message = get_object_or_404(Message, pk=message_id)
        project = get_object_or_404(AnalysisProject, pk=project_id)

        try:
            draft = services.generate_draft_for_message(message, project)
        except Exception as e:
            return Response(
                {"error": "Draft generation failed.", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(AIDraftSerializer(draft).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="approve-and-send")
    def approve_and_send(self, request, pk=None):
        draft = self.get_object()
        outgoing = services.approve_and_send_draft(draft)
        return Response(OutgoingMessageSerializer(outgoing).data)

    @action(detail=True, methods=["patch"], url_path="edit")
    def edit(self, request, pk=None):
        draft = self.get_object()
        edited_text = request.data.get("edited_text", "")
        draft = services.update_draft(draft, edited_text)
        return Response(AIDraftSerializer(draft).data)