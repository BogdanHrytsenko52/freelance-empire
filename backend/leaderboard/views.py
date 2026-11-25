from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from companies.models import Company

from .serializers import LeaderboardEntrySerializer

ALLOWED_SORT_FIELDS: dict[str, tuple[str, ...]] = {
    "reputation": ("-reputation", "-balance", "-completed_contracts", "id"),
    "-reputation": ("-reputation", "-balance", "-completed_contracts", "id"),
    "balance": ("-balance", "-reputation", "-completed_contracts", "id"),
    "-balance": ("-balance", "-reputation", "-completed_contracts", "id"),
    "completed_contracts": ("-completed_contracts", "-reputation", "-balance", "id"),
    "-completed_contracts": ("-completed_contracts", "-reputation", "-balance", "id"),
}


class LeaderboardListView(generics.ListAPIView):
    serializer_class = LeaderboardEntrySerializer
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (доступ до лідерборду):
    # Варіант 1 (поточний): достатньо IsAuthenticated (бачити рейтинг може
    #   кожен залогінений гравець, навіть до створення власної компанії).
    # Варіант 2: додати HasCompany, якщо рейтинг має бути доступний лише зі студією.
    # =========================================================================
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        sort_param = (
            self.request.GET.get("ordering")
            or self.request.GET.get("sort")
            or "reputation"
        ).lower().strip()

        order_fields = ALLOWED_SORT_FIELDS.get(
            sort_param,
            ALLOWED_SORT_FIELDS["reputation"],
        )
        return Company.objects.all().order_by(*order_fields)

    def _get_start_place(self) -> int:
        paginator = getattr(self, "paginator", None)
        if paginator is None:
            return 1

        # Для PageNumberPagination: (номер_сторінки - 1) * розмір_сторінки + 1
        page_obj = getattr(paginator, "page", None)
        if page_obj is not None:
            return (page_obj.number - 1) * page_obj.paginator.per_page + 1

        # Для LimitOffsetPagination: offset + 1
        offset = getattr(paginator, "offset", 0)
        return int(offset) + 1

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            items = list(page)
            start_place = self._get_start_place()
            for index, company in enumerate(items, start=start_place):
                company.place = index
            serializer = self.get_serializer(items, many=True)
            return self.get_paginated_response(serializer.data)

        items = list(queryset)
        for index, company in enumerate(items, start=1):
            company.place = index
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
