from django.db import models
from django.conf import settings


class AnalysisProject(models.Model):
    class DataSourceType(models.TextChoices):
        SMS = "sms", "SMS"
        SURVEY = "survey", "Survey"
        EMAIL = "email", "Email"
        PORTAL = "portal", "Web Portal"
        WHATSAPP  = "whatsapp",  "WhatsApp" 

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    data_source_type = models.CharField(
        max_length=50, choices=DataSourceType.choices, default=DataSourceType.PORTAL
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analysis_projects"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["created_by", "created_at"])]

    def __str__(self):
        return f"Project: {self.name}"


class ProjectParticipant(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        CONTRIBUTOR = "contributor", "Contributor"
        VIEWER = "viewer", "Viewer"

    project = models.ForeignKey(
        AnalysisProject, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participations"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_participants"
        unique_together = [("project", "user")]
        indexes = [models.Index(fields=["project", "user"])]

    def __str__(self):
        return f"{self.user} → {self.project} [{self.role}]"