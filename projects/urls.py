from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalysisProjectViewSet

router = DefaultRouter()
router.register(r"", AnalysisProjectViewSet, basename="projects")

urlpatterns = [path("", include(router.urls))]