"""Request and response serializers for authentication endpoints."""

from django.contrib.auth import password_validation
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .services import register_user


class UserSerializer(serializers.ModelSerializer):
    """Public representation of the authenticated user without sensitive fields."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "date_joined", "is_active")
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """Registration input. Role and staff fields are deliberately not accepted."""

    username = serializers.CharField(
        max_length=User._meta.get_field("username").max_length
    )
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value: str) -> str:
        validator = User._meta.get_field("username").validators[0]
        validator(value)
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with that username already exists."
            )
        return value

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return email

    def validate(self, attrs: dict) -> dict:
        protected_fields = {"role", "is_staff", "is_superuser"}
        attempted_fields = protected_fields.intersection(self.initial_data)
        if attempted_fields:
            raise serializers.ValidationError(
                {
                    field: "This field cannot be set during registration."
                    for field in attempted_fields
                }
            )
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password confirmation does not match."}
            )
        candidate = User(username=attrs["username"], email=attrs["email"])
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"password": list(error.messages)}
            ) from error
        return attrs

    def create(self, validated_data: dict) -> User:
        validated_data.pop("password_confirm")
        return register_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Standard SimpleJWT pair response with a safe current-user summary."""

    @classmethod
    def get_token(cls, user: User):
        return super().get_token(user)

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        update_last_login(None, self.user)
        data["user"] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
