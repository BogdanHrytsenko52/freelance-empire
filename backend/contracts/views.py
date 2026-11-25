from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from companies.permissions import HasCompany
from projects.models import Project
from projects.serializers import ProjectSerializer

from .models import Contract, ContractStatus
from .serializers import ContractSerializer
from .services import accept_contract


def _visible_contracts_queryset(company):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (видимість контрактів у GET /api/contracts/):
    # Поточний варіант: гравець бачить вільні контракти на біржі
    # (company=None, status="available") + усі контракти своєї компанії
    # (negotiating, accepted, completed, failed).
    # Чужі контракти інших компаній повністю приховані (захист від IDOR).
    # =========================================================================
    return Contract.objects.filter(
        Q(company__isnull=True, status=ContractStatus.AVAILABLE)
        | Q(company=company)
    )


class ContractListView(generics.ListAPIView):
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Contract.objects.none()

        queryset = _visible_contracts_queryset(self.request.user.company)

        status_param = self.request.GET.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.lower().strip())

        difficulty_param = self.request.GET.get("difficulty")
        if difficulty_param:
            try:
                difficulty_value = int(difficulty_param)
            except (TypeError, ValueError):
                return Contract.objects.none()
            queryset = queryset.filter(difficulty=difficulty_value)

        return queryset


class ContractDetailView(generics.RetrieveAPIView):
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Contract.objects.none()

        return _visible_contracts_queryset(self.request.user.company)


class ContractAcceptView(generics.GenericAPIView):
    serializer_class = serializers.Serializer
    permission_classes = [IsAuthenticated, HasCompany]

    def post(self, request, *args, **kwargs):
        project = accept_contract(
            company=request.user.company,
            contract_id=kwargs["pk"],
        )
        project = (
            Project.objects.select_related("contract")
            .prefetch_related("tasks__assignments")
            .get(pk=project.pk)
        )
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )
