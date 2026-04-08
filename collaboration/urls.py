from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DiscussionViewSet

router = DefaultRouter()
router.register(r"discussions", DiscussionViewSet, basename="discussions")

urlpatterns = [path("", include(router.urls))]