from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIDraftViewSet

router = DefaultRouter()
router.register(r"drafts", AIDraftViewSet, basename="ai-drafts")

urlpatterns = [path("", include(router.urls))]