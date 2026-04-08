from django.db import models
from django.conf import settings
from projects.models import AnalysisProject


class Discussion(models.Model):
    class RelatedType(models.TextChoices):
        MESSAGE = "message", "Message"
        REPORT = "report", "Report"
        INSIGHT = "insight", "Insight"

    project = models.ForeignKey(
        AnalysisProject, on_delete=models.CASCADE, related_name="discussions"
    )
    related_type = models.CharField(max_length=20, choices=RelatedType.choices)
    related_id = models.PositiveBigIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="discussions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "discussions"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["project", "related_type", "related_id"])]

    def __str__(self):
        return f"Discussion #{self.pk} on {self.related_type} #{self.related_id}"


class DiscussionParticipant(models.Model):
    class Role(models.TextChoices):
        CONTRIBUTOR = "contributor", "Contributor"
        VIEWER = "viewer", "Viewer"

    discussion = models.ForeignKey(
        Discussion, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="discussion_participations"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)

    class Meta:
        db_table = "discussion_participants"
        unique_together = [("discussion", "user")]

    def __str__(self):
        return f"{self.user} in Discussion #{self.discussion_id} [{self.role}]"


class Comment(models.Model):
    discussion = models.ForeignKey(
        Discussion, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["discussion", "created_at"])]

    def __str__(self):
        return f"Comment #{self.pk} by {self.user} on Discussion #{self.discussion_id}"