from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


def register_user(validated_data: dict) -> User:
    """Create and return a new user."""
    return User.objects.create_user(**validated_data)


def get_tokens_for_user(user: User) -> dict:
    """Generate JWT access and refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }