from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from projects.models import AnalysisProject, ProjectParticipant
from users.models import User
from .models import Discussion, DiscussionParticipant
from .serializers import (
    DiscussionSerializer, CommentSerializer, CreateDiscussionSerializer, InviteParticipantsSerializer,
    DiscussionParticipantSerializer,
)
from . import services


class DiscussionViewSet(viewsets.ModelViewSet):
    serializer_class = DiscussionSerializer

    def get_queryset(self):
        """
        Used only for LIST action.
        Requires ?project_id= query param.
        """
        project_id = self.request.query_params.get("project_id")
        if not project_id:
            return Discussion.objects.none()

        is_member = ProjectParticipant.objects.filter(
            project_id=project_id,
            user=self.request.user
        ).exists()

        if not is_member:
            return Discussion.objects.none()

        return Discussion.objects.filter(
            project_id=project_id
        ).select_related("project", "created_by").prefetch_related(
            "comments__user", "participants__user"
        ).order_by("-created_at")

    def get_object(self):
        """
        Override for ALL detail actions (retrieve, add_comment, invite, etc.)
        
        Does a direct pk lookup instead of going through get_queryset(),
        which would crash for any request that doesn't have ?project_id=
        in the URL — including comment POSTs, invite POSTs, etc.

        Still enforces access: user must be a project member OR a direct
        discussion participant (for invited users not in the project).
        """
        pk = self.kwargs.get("pk")

        discussion = get_object_or_404(
            Discussion.objects.select_related("project", "created_by")
            .prefetch_related("comments__user", "participants__user"),
            pk=pk,
        )

        # Access check — project member OR direct participant
        is_project_member = ProjectParticipant.objects.filter(
            project=discussion.project,
            user=self.request.user,
        ).exists()

        is_participant = DiscussionParticipant.objects.filter(
            discussion=discussion,
            user=self.request.user,
        ).exists()

        if not is_project_member and not is_participant:
            raise PermissionDenied(
                "You do not have access to this discussion."
            )

        return discussion

    def create(self, request):
        serializer = CreateDiscussionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = get_object_or_404(AnalysisProject, pk=data["project"])
        invited_emails = data.get("invited_emails", [])

        discussion = services.create_discussion(
            project=project,
            user=request.user,
            data={
                "related_type": data["related_type"],
                "related_id":   data["related_id"],
            },
            invited_emails=invited_emails,
        )

        return Response(
            DiscussionSerializer(discussion).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="comments")
    def add_comment(self, request, pk=None):
        """
        POST /collaboration/discussions/<id>/comments/
        
        get_object() now does a direct pk lookup — no ?project_id= needed.
        """
        discussion = self.get_object()

        content = request.data.get("content", "").strip()
        if not content:
            return Response(
                {"error": "Comment cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = services.add_comment(discussion, request.user, content)
        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="invite")
    def invite(self, request, pk=None):
        """
        POST /collaboration/discussions/<id>/invite/
        """
        discussion = self.get_object()

        serializer = InviteParticipantsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = services.invite_participants(
            discussion=discussion,
            invited_by=request.user,
            emails=serializer.validated_data["emails"],
        )

        return Response({
            "invited":    [{"email": u.email, "name": u.name} for u in result["invited"]],
            "not_found":  result["not_found"],
            "already_in": [{"email": u.email, "name": u.name} for u in result["already_in"]],
        })

    @action(detail=True, methods=["delete"], url_path="remove-participant")
    def remove_participant(self, request, pk=None):
        """
        DELETE /collaboration/discussions/<id>/remove-participant/
        """
        discussion     = self.get_object()
        user_to_remove = get_object_or_404(User, pk=request.data.get("user_id"))
        services.remove_participant(discussion, user_to_remove, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="participants")
    def participants(self, request, pk=None):
        """
        GET /collaboration/discussions/<id>/participants/
        """
        discussion = self.get_object()
        parts = DiscussionParticipant.objects.filter(
            discussion=discussion
        ).select_related("user")
        return Response(
            DiscussionParticipantSerializer(parts, many=True).data
        )


class MyDiscussionsView(APIView):
    """
    GET /api/v1/collaboration/my-discussions/

    Returns all discussions the logged-in user has been added to
    as a DiscussionParticipant — across all projects.
    This is separate from project-level access.
    """

    def get(self, request):
        try:
            discussions = services.get_user_discussions(request.user)
            serializer  = DiscussionSerializer(
                discussions, many=True, context={"request": request}
            )
            return Response(serializer.data)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )