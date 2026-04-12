from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DiscussionViewSet, MyDiscussionsView

router = DefaultRouter()
router.register(r"discussions", DiscussionViewSet, basename="discussions")

urlpatterns = [
    path("", include(router.urls)),
    path("my-discussions/", MyDiscussionsView.as_view(), name="my-discussions"),
]