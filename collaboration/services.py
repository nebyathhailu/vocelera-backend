import logging
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied, ValidationError
from projects.models import ProjectParticipant
from .models import Discussion, DiscussionParticipant, Comment

User = get_user_model()
logger = logging.getLogger(__name__)


def _assert_project_member(project, user):
    if not ProjectParticipant.objects.filter(project=project, user=user).exists():
        raise PermissionDenied(
            "You must be a project member to interact with discussions."
        )


def _assert_can_comment(discussion, user):
    is_project_member = ProjectParticipant.objects.filter(
        project=discussion.project, user=user
    ).exists()

    is_discussion_participant = DiscussionParticipant.objects.filter(
        discussion=discussion, user=user
    ).exists()

    if not is_project_member and not is_discussion_participant:
        raise PermissionDenied("You do not have access to this discussion.")

    if is_project_member and not is_discussion_participant:
        membership = ProjectParticipant.objects.get(
            project=discussion.project, user=user
        )
        if membership.role == "viewer":
            raise PermissionDenied(
                "Viewers cannot comment. Ask the discussion owner to invite you directly."
            )


def create_discussion(project, user, data, invited_emails=None):
    _assert_project_member(project, user)

    discussion = Discussion.objects.create(
        project=project, created_by=user, **data
    )

    DiscussionParticipant.objects.create(
        discussion=discussion,
        user=user,
        role=DiscussionParticipant.Role.CONTRIBUTOR,
    )

    if invited_emails:
        invite_participants(discussion, invited_by=user, emails=invited_emails)

    logger.info(
        "Discussion #%s created by %s with %d invitees",
        discussion.pk, user.email, len(invited_emails or [])
    )
    return discussion


def invite_participants(discussion, invited_by, emails):
    """
    Invite users to a discussion by email.
    Only contributors of the discussion can invite others.

    Returns:
        dict: { "invited": [User], "not_found": [str], "already_in": [User] }
    """
    # Verify the inviter is a contributor in this discussion
    caller_participant = DiscussionParticipant.objects.filter(
        discussion=discussion, user=invited_by
    ).first()

    if not caller_participant or caller_participant.role == DiscussionParticipant.Role.VIEWER:
        raise PermissionDenied(
            "Only discussion contributors can invite participants."
        )

    invited, not_found, already_in = [], [], []

    for email in emails:
        email = email.strip().lower()
        if not email:
            continue

        try:
            target_user = User.objects.get(email=email)
        except User.DoesNotExist:
            not_found.append(email)
            continue

        participant, created = DiscussionParticipant.objects.get_or_create(
            discussion=discussion,
            user=target_user,
            defaults={"role": DiscussionParticipant.Role.CONTRIBUTOR},
        )

        if created:
            invited.append(target_user)
            logger.info(
                "User %s invited to discussion #%s", email, discussion.pk
            )
        else:
            already_in.append(target_user)

    return {
        "invited":    invited,
        "not_found":  not_found,
        "already_in": already_in,
    }


def remove_participant(discussion, user_to_remove, requested_by):
    is_creator = discussion.created_by == requested_by
    is_project_owner = ProjectParticipant.objects.filter(
        project=discussion.project,
        user=requested_by,
        role=ProjectParticipant.Role.OWNER,
    ).exists()

    if not is_creator and not is_project_owner:
        raise PermissionDenied(
            "Only the discussion creator or project owner can remove participants."
        )

    if user_to_remove == discussion.created_by:
        raise ValidationError("Cannot remove the discussion creator.")

    DiscussionParticipant.objects.filter(
        discussion=discussion, user=user_to_remove
    ).delete()


def add_comment(discussion, user, content):
    _assert_can_comment(discussion, user)

    DiscussionParticipant.objects.get_or_create(
        discussion=discussion,
        user=user,
        defaults={"role": DiscussionParticipant.Role.CONTRIBUTOR},
    )

    return Comment.objects.create(
        discussion=discussion,
        user=user,
        content=content,
    )


def get_user_discussions(user):
    """
    All discussions the user has been added to as a DiscussionParticipant.
    Powers the My Contributions tab — works across all projects.
    """
    discussion_ids = DiscussionParticipant.objects.filter(
        user=user
    ).values_list("discussion_id", flat=True)

    return Discussion.objects.filter(
        id__in=discussion_ids
    ).select_related("project", "created_by").prefetch_related(
        "comments__user", "participants__user"
    ).order_by("-created_at")