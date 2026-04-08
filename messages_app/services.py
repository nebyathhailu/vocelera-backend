from typing import List
from .models import Message, Citizen
from projects.models import AnalysisProject


def create_message(project: AnalysisProject, data: dict) -> Message:
    return Message.objects.create(project=project, **data)


def bulk_import_messages(project: AnalysisProject, messages_data: List[dict]) -> int:
    """
    Efficiently bulk-import citizen messages into a project.

    Returns:
        int: Number of messages imported.
    """
    objs = [Message(project=project, **m) for m in messages_data]
    created = Message.objects.bulk_create(objs, ignore_conflicts=True)
    return len(created)


def get_project_messages(project_id: int):
    return Message.objects.filter(project_id=project_id).select_related("citizen")


def get_message_contents_for_project(project_id: int) -> List[str]:
    return list(
        Message.objects.filter(project_id=project_id)
        .values_list("content", flat=True)
        .order_by("-timestamp")[:1000]
    )