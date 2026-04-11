from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from projects.models import ProjectParticipant
from collaboration.models import DiscussionParticipant
from .serializers import MessageSerializer, CitizenSerializer, BulkMessageSerializer
from .models import Message, Citizen
from . import services


class CitizenViewSet(viewsets.ModelViewSet):
    queryset = Citizen.objects.all()
    serializer_class = CitizenSerializer


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer

    def get_queryset(self):
        project_id = (
            self.kwargs.get("project_pk")
            or self.request.query_params.get("project_id")
            or self.request.query_params.get("projects")
        )
        if not project_id:
            return Message.objects.none()

        user = self.request.user

        # Full project members see all messages
        if ProjectParticipant.objects.filter(project_id=project_id, user=user).exists():
            return services.get_project_messages(project_id)

        # Discussion-only invitees see only messages they were invited to discuss
        invited_message_ids = DiscussionParticipant.objects.filter(
            user=user,
            discussion__project_id=project_id,
            discussion__related_type="message",
        ).values_list("discussion__related_id", flat=True)

        if invited_message_ids:
            return Message.objects.filter(
                project_id=project_id,
                id__in=invited_message_ids,
            )

        return Message.objects.none()

    def perform_create(self, serializer):
        project_id = self.request.data.get("project")
        serializer.save(project_id=project_id)

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        serializer = BulkMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project_id = request.data.get("project_id")
        count = services.bulk_import_messages(
            project_id=project_id,
            messages_data=serializer.validated_data["messages"],
        )
        return Response({"imported": count}, status=status.HTTP_201_CREATED)