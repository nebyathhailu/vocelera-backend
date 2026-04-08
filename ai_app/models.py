from django.db import models
from projects.models import AnalysisProject
from messages_app.models import Message, Citizen


class AIDraft(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        SENT = "sent", "Sent"
        REJECTED = "rejected", "Rejected"

    project = models.ForeignKey(
        AnalysisProject, on_delete=models.CASCADE, related_name="ai_drafts"
    )
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="ai_drafts"
    )
    generated_text = models.TextField()
    edited_text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_drafts"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["project", "status"])]

    def __str__(self):
        return f"Draft #{self.pk} [{self.status}] for Message #{self.message_id}"


class OutgoingMessage(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    citizen = models.ForeignKey(Citizen, on_delete=models.SET_NULL, null=True, related_name="outgoing_messages")
    draft = models.OneToOneField(AIDraft, on_delete=models.CASCADE, related_name="outgoing_message")
    sent_text = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "outgoing_messages"
        indexes = [models.Index(fields=["citizen", "status"])]

    def __str__(self):
        return f"OutgoingMessage #{self.pk} → {self.citizen} [{self.status}]"