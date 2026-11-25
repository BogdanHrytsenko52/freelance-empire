from rest_framework import generics, serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from companies.permissions import HasCompany

from .models import Notification, NotificationType
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()

        queryset = Notification.objects.filter(company=self.request.user.company)

        is_read_param = self.request.GET.get("is_read")
        if is_read_param is not None:
            normalized = is_read_param.lower().strip()
            if normalized in {"true", "1"}:
                queryset = queryset.filter(is_read=True)
            elif normalized in {"false", "0"}:
                queryset = queryset.filter(is_read=False)
            else:
                return Notification.objects.none()

        type_param = self.request.GET.get("type")
        if type_param:
            normalized_type = type_param.lower().strip()
            if normalized_type not in set(NotificationType.values):
                return Notification.objects.none()
            queryset = queryset.filter(type=normalized_type)

        return queryset


class NotificationMarkReadView(generics.GenericAPIView):
    serializer_class = serializers.Serializer
    permission_classes = [IsAuthenticated, HasCompany]

    def post(self, request, *args, **kwargs):
        try:
            notification = Notification.objects.get(
                pk=kwargs["pk"],
                company=request.user.company,
            )
        except Notification.DoesNotExist as exc:
            raise NotFound("Сповіщення не знайдено.") from exc

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )
