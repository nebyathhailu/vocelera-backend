from django.db import models
from projects.models import AnalysisProject


class Citizen(models.Model):
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    # WhatsApp-specific identifier (WaId from Twilio payload)
    whatsapp_id = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    class Meta:
        db_table = "citizens"

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.phone_number})"


class Message(models.Model):
    class Source(models.TextChoices):
        SMS       = "sms",       "SMS"
        EMAIL     = "email",     "Email"
        PORTAL    = "portal",    "Web Portal"
        SURVEY    = "survey",    "Survey"
        WHATSAPP  = "whatsapp",  "WhatsApp"  

    project  = models.ForeignKey(
        AnalysisProject, on_delete=models.CASCADE, related_name="messages"
    )
    citizen  = models.ForeignKey(
        Citizen, on_delete=models.SET_NULL, null=True, related_name="messages"
    )
    content    = models.TextField()
    source     = models.CharField(max_length=20, choices=Source.choices)
    timestamp  = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Twilio MessageSid — used for idempotent deduplication
    external_id = models.CharField(
        max_length=64, blank=True, null=True, unique=True, db_index=True
    )

    class Meta:
        db_table = "messages"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["project", "timestamp"]),
            models.Index(fields=["citizen", "project"]),
            models.Index(fields=["source", "project"]),   # filter by WhatsApp source
        ]

    def __str__(self):
        return f"Message #{self.pk} from {self.citizen} [{self.source}]"