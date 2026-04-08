from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MessageViewSet, CitizenViewSet

router = DefaultRouter()
router.register(r"citizens", CitizenViewSet, basename="citizens")
router.register(r"", MessageViewSet, basename="messages")

urlpatterns = [path("", include(router.urls))]