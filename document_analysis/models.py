from django.db import models
from django.conf import settings
from projects.models import AnalysisProject


class DocumentAnalysis(models.Model):
    """
    Stores an uploaded document and its AI-generated analysis.
    Supports CSV, PDF, and Excel (xlsx/xls).
    """

    class Status(models.TextChoices):
        PENDING    = "pending",    "Pending"
        PROCESSING = "processing", "Processing"
        DONE       = "done",       "Done"
        FAILED     = "failed",     "Failed"

    class DocumentType(models.TextChoices):
        CSV   = "csv",  "CSV"
        PDF   = "pdf",  "PDF"
        EXCEL = "xlsx", "Excel"

    project      = models.ForeignKey(
        AnalysisProject,
        on_delete=models.CASCADE,
        related_name="document_analyses",
        null=True, blank=True,
        help_text="Optional: link analysis to a project"
    )
    uploaded_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="document_analyses",
    )
    file         = models.FileField(upload_to="document_uploads/%Y/%m/")
    file_name    = models.CharField(max_length=255)
    document_type = models.CharField(max_length=10, choices=DocumentType.choices)
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # AI output fields
    summary      = models.TextField(blank=True)
    key_themes   = models.JSONField(default=list, blank=True)
    statistics   = models.JSONField(default=dict, blank=True)
    insights     = models.JSONField(default=list, blank=True)
    recommendations = models.TextField(blank=True)
    raw_ai_response = models.TextField(blank=True)

    error_message = models.TextField(blank=True)
    row_count     = models.IntegerField(null=True, blank=True)
    page_count    = models.IntegerField(null=True, blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "document_analyses"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["uploaded_by", "created_at"]),
        ]

    def __str__(self):
        return f"DocumentAnalysis #{self.pk} [{self.file_name}] — {self.status}"