from django.contrib.auth import get_user_model
from .models import Discussion, DiscussionParticipant, Comment
from projects.models import AnalysisProject

User = get_user_model()


def create_discussion(project: AnalysisProject, user, data: dict,
                      invited_emails: list = None) -> Discussion:
    data.pop("project", None)
    discussion = Discussion.objects.create(project=project, created_by=user, **data)

    # Creator is always a contributor
    DiscussionParticipant.objects.create(
        discussion=discussion,
        user=user,
        role=DiscussionParticipant.Role.CONTRIBUTOR,
    )

    # Invite any emails provided at creation time
    if invited_emails:
        invite_by_emails(discussion, invited_emails)

    return discussion


def add_comment(discussion: Discussion, user, content: str) -> Comment:
    DiscussionParticipant.objects.get_or_create(
        discussion=discussion,
        user=user,
        defaults={"role": DiscussionParticipant.Role.CONTRIBUTOR},
    )
    return Comment.objects.create(discussion=discussion, user=user, content=content)


def invite_by_emails(discussion: Discussion, emails: list) -> dict:
    invited = []
    not_found = []
    already_in = []

    for email in emails:
        email = email.strip().lower()
        if not email:
            continue
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            not_found.append(email)
            continue

        participant, created = DiscussionParticipant.objects.get_or_create(
            discussion=discussion,
            user=user,
            defaults={"role": DiscussionParticipant.Role.CONTRIBUTOR},
        )
        if created:
            invited.append({"email": user.email, "name": user.name})
        else:
            already_in.append({"email": user.email, "name": user.name})

    return {"invited": invited, "not_found": not_found, "already_in": already_in}


def remove_participant(discussion: Discussion, requesting_user, user_id: int):
    # Only the discussion creator can remove participants
    if discussion.created_by_id != requesting_user.id:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Only the discussion creator can remove participants.")

    # Cannot remove the creator
    if discussion.created_by_id == user_id:
        from rest_framework.exceptions import ValidationError
        raise ValidationError("The discussion creator cannot be removed.")

    DiscussionParticipant.objects.filter(
        discussion=discussion,
        user_id=user_id,
    ).delete()