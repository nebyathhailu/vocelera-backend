from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from utils.permissions import IsProjectParticipant
from django.conf import settings
from .models import AnalysisProject, ProjectParticipant
from .serializers import AnalysisProjectSerializer, ProjectParticipantSerializer
from . import services


class AnalysisProjectViewSet(viewsets.ModelViewSet):
    serializer_class = AnalysisProjectSerializer

    def get_queryset(self):
        return services.get_user_projects(self.request.user)

    def perform_create(self, serializer):
        services.create_project(
            user=self.request.user,
            data=serializer.validated_data,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = services.create_project(request.user, serializer.validated_data)
        return Response(
            AnalysisProjectSerializer(project).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="add-participant")
    def add_participant(self, request, pk=None):
        project = self.get_object()
        participant = services.add_participant(
            project=project,
            user_id=request.data.get("user_id"),
            role=request.data.get("role", ProjectParticipant.Role.VIEWER),
        )
        return Response(ProjectParticipantSerializer(participant).data)
    

    @action(detail=True, methods=["get"], url_path="whatsapp-config",permission_classes=[AllowAny])
    def whatsapp_config(self, request, pk=None):
        """
        Returns everything needed to generate a feedback link / QR code.
        The sandbox join keyword and number come from settings so they
        stay in one place when you move to a production number.
        """
        project = get_object_or_404(AnalysisProject, pk=pk)
        sandbox_number  = getattr(settings, "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        # Strip the "whatsapp:" prefix for display
        display_number  = sandbox_number.replace("whatsapp:", "")
        sandbox_keyword = getattr(settings, "TWILIO_SANDBOX_KEYWORD", "join top-everywhere")

        return Response({
            "project_id":      project.id,
            "project_name":    project.name,
            "display_number":  display_number,
            "sandbox_keyword": sandbox_keyword,
            "is_sandbox":      getattr(settings, "TWILIO_IS_SANDBOX", True),
            # wa.me deep link — opens WhatsApp with the join message pre-filled
            "whatsapp_link":   f"https://wa.me/{display_number.lstrip('+').replace(' ','')}?text={sandbox_keyword.replace(' ', '%20')}",
        })