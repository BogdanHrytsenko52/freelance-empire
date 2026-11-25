from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Company
from .serializers import (
    CompanyCreateSerializer,
    CompanySerializer,
    CompanyUpdateSerializer,
)


class CompanyCreateView(generics.CreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanyCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save(owner=request.user)
        output = CompanySerializer(company)
        return Response(output.data, status=status.HTTP_201_CREATED)


class MyCompanyView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self) -> Company:
        try:
            return self.request.user.company
        except Company.DoesNotExist as exc:
            raise NotFound("Компанію ще не створено") from exc

    def get_serializer_class(self):
        if getattr(self.request, "method", None) == "PATCH":
            return CompanyUpdateSerializer
        return CompanySerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        return Response(CompanySerializer(company).data, status=status.HTTP_200_OK)
