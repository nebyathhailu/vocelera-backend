from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Discussion, Comment
from .serializers import DiscussionSerializer, CommentSerializer
from . import services
from projects.models import AnalysisProject
from django.shortcuts import get_object_or_404


class DiscussionViewSet(viewsets.ModelViewSet):
    serializer_class = DiscussionSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id:
            return Discussion.objects.filter(project_id=project_id).prefetch_related("comments")
        return Discussion.objects.none()

    def perform_create(self, serializer):
        project = get_object_or_404(AnalysisProject, pk=self.request.data.get("project"))
        services.create_discussion(
            project=project, user=self.request.user, data=serializer.validated_data
        )

    @action(detail=True, methods=["post"], url_path="comments")
    def add_comment(self, request, pk=None):
        discussion = self.get_object()
        comment = services.add_comment(
            discussion=discussion,
            user=request.user,
            content=request.data.get("content", ""),
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)