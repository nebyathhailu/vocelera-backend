from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.permissions import IsProjectParticipant
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