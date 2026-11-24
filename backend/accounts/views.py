"""DRF views for registration, JWT lifecycle, and current-user lookup."""

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)

TOKEN_RESPONSE = inline_serializer(
    name="TokenResponse",
    fields={
        "access": serializers.CharField(read_only=True),
        "refresh": serializers.CharField(read_only=True),
        "user": UserSerializer(read_only=True),
    },
)


class RegisterView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_register"

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        auth=[],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("User registered: id=%s", user.pk)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_login"

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: TOKEN_RESPONSE,
            401: OpenApiResponse(description="Invalid credentials"),
        },
        auth=[],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RefreshView(TokenRefreshView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_refresh"

    @extend_schema(auth=[])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=LogoutSerializer,
        responses={
            205: OpenApiResponse(description="Refresh token revoked"),
            400: OpenApiResponse(description="Invalid token"),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response(
                {"detail": "Refresh token is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.info("User logged out: id=%s", request.user.pk)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Authentication required"),
        }
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
