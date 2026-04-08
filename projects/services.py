from django.shortcuts import get_object_or_404
from .models import AnalysisProject, ProjectParticipant
from users.models import User


def create_project(user: User, data: dict) -> AnalysisProject:
    """Create a project and assign the creator as owner."""
    project = AnalysisProject.objects.create(created_by=user, **data)
    ProjectParticipant.objects.create(
        project=project, user=user, role=ProjectParticipant.Role.OWNER
    )
    return project


def get_user_projects(user: User):
    """Return all projects the user participates in."""
    project_ids = ProjectParticipant.objects.filter(user=user).values_list(
        "project_id", flat=True
    )
    return AnalysisProject.objects.filter(id__in=project_ids)


def add_participant(project: AnalysisProject, user_id: int, role: str) -> ProjectParticipant:
    user = get_object_or_404(User, pk=user_id)
    participant, _ = ProjectParticipant.objects.get_or_create(
        project=project, user=user, defaults={"role": role}
    )
    return participant