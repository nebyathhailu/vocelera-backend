from rest_framework import viewsets, status
from rest_framework.decorators import APIView, action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Discussion, DiscussionParticipant, Comment
from .serializers import DiscussionSerializer, CommentSerializer, DiscussionParticipantSerializer
from . import services
from projects.models import AnalysisProject

User = get_user_model()


class DiscussionViewSet(viewsets.ModelViewSet):
    serializer_class = DiscussionSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id:
            return Discussion.objects.filter(
                project_id=project_id
            ).prefetch_related("comments", "participants__user")
        return Discussion.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        project = data.pop("project")
        invited_emails = request.data.get("invited_emails", [])

        discussion = services.create_discussion(
            project=project,
            user=request.user,
            data=data,
            invited_emails=invited_emails,
        )
        return Response(
            DiscussionSerializer(discussion).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="my-discussions",
            url_name="my-discussions")
    def my_discussions(self, request):
        """All discussions the current user is a participant in, across all projects."""
        discussion_ids = DiscussionParticipant.objects.filter(
            user=request.user
        ).values_list("discussion_id", flat=True)
        qs = Discussion.objects.filter(
            id__in=discussion_ids
        ).prefetch_related("comments", "participants__user")
        serializer = DiscussionSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="comments")
    def add_comment(self, request, pk=None):
        discussion = self.get_object()
        comment = services.add_comment(
            discussion=discussion,
            user=request.user,
            content=request.data.get("content", ""),
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="invite")
    def invite(self, request, pk=None):
        discussion = self.get_object()
        emails = request.data.get("emails", [])
        result = services.invite_by_emails(discussion, emails)
        return Response(result)

    @action(detail=True, methods=["delete"], url_path="remove-participant")
    def remove_participant(self, request, pk=None):
        discussion = self.get_object()
        user_id = request.data.get("user_id")
        services.remove_participant(discussion, request.user, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="participants")
    def participants(self, request, pk=None):
        discussion = self.get_object()
        parts = discussion.participants.select_related("user")
        serializer = DiscussionParticipantSerializer(parts, many=True)
        return Response(serializer.data)

class MyDiscussionsView(APIView):
    """
    GET /collaboration/my-discussions/

    Returns every discussion thread the logged-in user has been
    added to as a DiscussionParticipant — across all projects.
    This powers the "My Contributions" / thread inbox view.
    """

    def get(self, request):
        discussions = services.get_user_discussions(request.user)
        return Response(DiscussionSerializer(discussions, many=True).data)