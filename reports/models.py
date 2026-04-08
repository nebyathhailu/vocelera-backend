from django.db import models
from projects.models import AnalysisProject


class Report(models.Model):
    project = models.ForeignKey(
        AnalysisProject, on_delete=models.CASCADE, related_name="reports"
    )
    summary = models.TextField()
    file_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.pk} for {self.project}"