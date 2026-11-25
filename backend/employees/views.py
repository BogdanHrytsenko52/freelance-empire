from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from companies.permissions import HasCompany

from .models import Candidate, Employee
from .serializers import (
    CandidateSerializer,
    EmployeeSerializer,
    HireCandidateSerializer,
)
from .services import fire_employee, hire_candidate


class EmployeeListView(generics.ListAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Employee.objects.none()

        queryset = Employee.objects.filter(
            company=self.request.user.company
        ).prefetch_related("skills")

        specialization = self.request.query_params.get("specialization")
        if specialization:
            queryset = queryset.filter(specialization=specialization.lower())

        return queryset


class CandidateListView(generics.ListAPIView):
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        queryset = Candidate.objects.filter(is_available=True)

        specialization = self.request.query_params.get("specialization")
        if specialization:
            queryset = queryset.filter(specialization=specialization.lower())

        return queryset


class HireCandidateView(generics.GenericAPIView):
    serializer_class = HireCandidateSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = hire_candidate(
            company=request.user.company,
            candidate_id=serializer.validated_data["candidate_id"],
        )
        return Response(
            EmployeeSerializer(employee).data,
            status=status.HTTP_201_CREATED,
        )


class FireEmployeeView(generics.GenericAPIView):
    serializer_class = serializers.Serializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Employee.objects.none()

        return Employee.objects.filter(company=self.request.user.company)

    def post(self, request, *args, **kwargs):
        employee = self.get_object()
        fire_employee(employee=employee)
        return Response(
            {"detail": "Працівника звільнено"},
            status=status.HTTP_200_OK,
        )
