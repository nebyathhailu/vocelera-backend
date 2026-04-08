from rest_framework.permissions import BasePermission
from projects.models import ProjectParticipant


class IsProjectParticipant(BasePermission):
    """
    Only allow access if the requesting user is a participant of the project.
    Expects 'project_id' in query params or request body.
    """

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