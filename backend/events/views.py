from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from companies.permissions import HasCompany

from .models import CompanyEvent, EventStatus
from .serializers import ChooseEventOptionSerializer, CompanyEventSerializer
from .services import choose_event_option


def _company_events_queryset(company):
    return (
        CompanyEvent.objects.filter(company=company)
        .select_related("template", "chosen_option")
        .prefetch_related("template__choices")
    )


class ActiveEventListView(generics.ListAPIView):
    serializer_class = CompanyEventSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CompanyEvent.objects.none()

        # В API_CONTRACT.md зафіксовано ліміт: не більше 2 активних івентів (контролює events_engine.py).
        return _company_events_queryset(self.request.user.company).filter(
            status=EventStatus.PENDING
        )


class EventHistoryListView(generics.ListAPIView):
    serializer_class = CompanyEventSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CompanyEvent.objects.none()

        return _company_events_queryset(self.request.user.company).filter(
            status__in=[EventStatus.RESOLVED, EventStatus.EXPIRED]
        )


class EventChooseView(generics.GenericAPIView):
    serializer_class = ChooseEventOptionSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = choose_event_option(
            company=request.user.company,
            event_id=kwargs["pk"],
            choice_id=serializer.validated_data["choice_id"],
        )
        event = _company_events_queryset(request.user.company).get(
            pk=result["event"].pk
        )

        # =====================================================================
        # TODO / УЗГОДЖЕННЯ (формат відповіді POST /api/events/{id}/choose/ — з Артемом):
        # В API_CONTRACT.md Артем просив повертати наслідки вибору.
        # Повертаємо оновлений об'єкт event + масив effects для швидкого показу в UI.
        # =====================================================================
        return Response(
            {
                "event": CompanyEventSerializer(event).data,
                "effects": result["effects"],
            },
            status=status.HTTP_200_OK,
        )
