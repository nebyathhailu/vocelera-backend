from django.urls import path
from .views import WhatsAppWebhookView

urlpatterns = [
    path(
        "<int:project_id>/whatsapp/",
        WhatsAppWebhookView.as_view(),
        name="twilio-whatsapp-webhook",
    ),
]