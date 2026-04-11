from rest_framework.permissions import BasePermission
from projects.models import ProjectParticipant
from collaboration.models import DiscussionParticipant


class IsProjectParticipant(BasePermission):
    """Only allow access if the requesting user is a project participant."""

    def has_permission(self, request, view):
        project_id = (
            view.kwargs.get("project_pk")
            or request.query_params.get("project_id")
            or request.data.get("project_id")
        )
        if not project_id:
            return False
        return ProjectParticipant.objects.filter(
            project_id=project_id, user=request.user
        ).exists()


class IsProjectOwnerOrContributor(BasePermission):
    """Restrict write actions to owners and contributors only."""

    def has_permission(self, request, view):
        project_id = (
            view.kwargs.get("project_pk")
            or request.query_params.get("project_id")
            or request.data.get("project_id")
        )
        if not project_id:
            return False
        return ProjectParticipant.objects.filter(
            project_id=project_id,
            user=request.user,
            role__in=[ProjectParticipant.Role.OWNER, ProjectParticipant.Role.CONTRIBUTOR],
        ).exists()


class IsProjectOrDiscussionParticipant(BasePermission):
    """
    Allow access if the user is either:
    - A project participant (any role), OR
    - A DiscussionParticipant on any discussion in this project
    This lets invited-only users see project resources they were invited to discuss.
    """

    def has_permission(self, request, view):
        project_id = (
            view.kwargs.get("project_pk")
            or request.query_params.get("project_id")
            or request.data.get("project_id")
        )
        if not project_id:
            return False

        # Full project member
        if ProjectParticipant.objects.filter(
            project_id=project_id, user=request.user
        ).exists():
            return True

        # Invited to at least one discussion in this project
        return DiscussionParticipant.objects.filter(
            discussion__project_id=project_id,
            user=request.user,
        ).exists()