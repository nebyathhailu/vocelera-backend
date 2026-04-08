from .models import Discussion, DiscussionParticipant, Comment
from users.models import User
from projects.models import AnalysisProject


def create_discussion(project: AnalysisProject, user: User, data: dict) -> Discussion:
    discussion = Discussion.objects.create(project=project, created_by=user, **data)
    DiscussionParticipant.objects.create(
        discussion=discussion,
        user=user,
        role=DiscussionParticipant.Role.CONTRIBUTOR,
    )
    return discussion


def add_comment(discussion: Discussion, user: User, content: str) -> Comment:
    DiscussionParticipant.objects.get_or_create(
        discussion=discussion,
        user=user,
        defaults={"role": DiscussionParticipant.Role.CONTRIBUTOR},
    )
    return Comment.objects.create(discussion=discussion, user=user, content=content)