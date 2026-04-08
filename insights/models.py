from django.db import models
from projects.models import AnalysisProject


class Insight(models.Model):
    project = models.ForeignKey(
        AnalysisProject, on_delete=models.CASCADE, related_name="insights"
    )
    theme = models.CharField(max_length=255, db_index=True)
    sentiment = models.CharField(
        max_length=20,
        choices=[
            ("positive", "Positive"),
            ("negative", "Negative"),
            ("neutral", "Neutral"),
            ("mixed", "Mixed"),
        ],
    )
    priority_score = models.FloatField(default=0.0, db_index=True)
    frequency = models.IntegerField(default=0)
    trend_data = models.JSONField(default=dict, blank=True)
    policy_suggestion = models.TextField(blank=True)
    service_improvement = models.TextField(blank=True)
    interpretation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "insights"
        ordering = ["-priority_score", "-frequency"]
        indexes = [
            models.Index(fields=["project", "priority_score"]),
            models.Index(fields=["project", "sentiment"]),
        ]

    def __str__(self):
        return f"Insight: {self.theme} [{self.sentiment}] — Score: {self.priority_score}"