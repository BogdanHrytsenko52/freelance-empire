from rest_framework import serializers

from contracts.serializers import ContractSerializer

from .models import Project, ProjectTask


class ProjectTaskSerializer(serializers.ModelSerializer):
    assignee_ids = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTask
        fields = [
            "id",
            "title",
            "required_specialization",
            "work_total",
            "work_done",
            "status",
            "assignee_ids",
        ]
        read_only_fields = fields

    def get_assignee_ids(self, obj: ProjectTask) -> list[int]:
        return [assignment.employee_id for assignment in obj.assignments.all()]


class ProjectSerializer(serializers.ModelSerializer):
    contract = ContractSerializer(read_only=True)
    tasks = ProjectTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "contract",
            "status",
            "progress",
            "quality",
            "deadline",
            "tasks",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields


class ProjectTaskAssignmentSerializer(serializers.Serializer):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат тіла запиту assign / unassign — з Артемом):
    # В API_CONTRACT.md зазначено, що assign та unassign приймають працівника й завдання.
    # Закладаємо стандартний формат {"task_id": <int>, "employee_id": <int>}.
    # =========================================================================
    task_id = serializers.IntegerField(min_value=1)
    employee_id = serializers.IntegerField(min_value=1)
