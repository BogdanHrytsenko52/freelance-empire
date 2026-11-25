from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from companies.permissions import HasCompany

from .models import Project
from .serializers import ProjectSerializer, ProjectTaskAssignmentSerializer
from .services import (
    assign_employee_to_task,
    submit_project,
    unassign_employee_from_task,
)


def _company_projects_queryset(company):
    return (
        Project.objects.filter(company=company)
        .select_related("contract")
        .prefetch_related("tasks__assignments")
    )


class ProjectListView(generics.ListAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Project.objects.none()

        queryset = _company_projects_queryset(self.request.user.company)

        status_param = self.request.GET.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.lower().strip())

        return queryset


class ProjectDetailView(generics.RetrieveAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Project.objects.none()

        return _company_projects_queryset(self.request.user.company)


class ProjectAssignView(generics.GenericAPIView):
    serializer_class = ProjectTaskAssignmentSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = assign_employee_to_task(
            company=request.user.company,
            project_id=kwargs["pk"],
            task_id=serializer.validated_data["task_id"],
            employee_id=serializer.validated_data["employee_id"],
        )
        project = _company_projects_queryset(request.user.company).get(pk=project.pk)
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)


class ProjectUnassignView(generics.GenericAPIView):
    serializer_class = ProjectTaskAssignmentSerializer
    permission_classes = [IsAuthenticated, HasCompany]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = unassign_employee_from_task(
            company=request.user.company,
            project_id=kwargs["pk"],
            task_id=serializer.validated_data["task_id"],
            employee_id=serializer.validated_data["employee_id"],
        )
        project = _company_projects_queryset(request.user.company).get(pk=project.pk)
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)


class ProjectSubmitView(generics.GenericAPIView):
    serializer_class = serializers.Serializer
    permission_classes = [IsAuthenticated, HasCompany]

    def post(self, request, *args, **kwargs):
        submission = submit_project(
            company=request.user.company,
            project_id=kwargs["pk"],
        )
        project = _company_projects_queryset(request.user.company).get(
            pk=submission["project"].pk
        )

        # =====================================================================
        # TODO / УЗГОДЖЕННЯ (формат відповіді POST /api/projects/{id}/submit/ — з Артемом):
        # В API_CONTRACT.md (п. 4.7) Артем просив повернути результат, виплату
        # та зміну репутації. Суму payout віддаємо рядком (Money), як і всі гроші.
        # =====================================================================
        return Response(
            {
                "result": submission["result"],
                "payout": str(submission["payout"]),
                "reputation_change": submission["reputation_change"],
                "is_overdue": submission["is_overdue"],
                "project": ProjectSerializer(project).data,
            },
            status=status.HTTP_200_OK,
        )
