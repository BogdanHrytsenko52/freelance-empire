from rest_framework import serializers

from .models import Candidate, Employee, EmployeeAvailability, EmployeeSkill


class EmployeeSkillSerializer(serializers.ModelSerializer):
    skill = serializers.CharField(source="skill_type", read_only=True)

    class Meta:
        model = EmployeeSkill
        fields = ["skill", "value"]
        read_only_fields = fields


class EmployeeSerializer(serializers.ModelSerializer):
    skills = EmployeeSkillSerializer(many=True, read_only=True)
    productivity = serializers.FloatField(read_only=True)
    # TODO / УЗГОДЖЕННЯ (is_available vs availability):
    # Віддаємо обидва поля: is_available (bool) для поточних типів Артема (game.ts)
    # і availability ("available" | "busy" | "sick") для точного відображення станів симуляції.
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "name",
            "specialization",
            "level",
            "salary",
            "productivity",
            "availability",
            "is_available",
            "skills",
            "hired_at",
        ]
        read_only_fields = fields

    def get_is_available(self, obj: Employee) -> bool:
        return obj.availability == EmployeeAvailability.AVAILABLE


class CandidateSerializer(serializers.ModelSerializer):
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (формат Candidate.skills у відповіді API):
    # У БД поле зберігається як словник {"coding": 65} (гарантує унікальність ключів).
    # Варіант 1 (поточний, під game.ts Артема): віддавати масивом [{"skill": "coding", "value": 65}],
    #   щоб формат збігався з Employee.skills.
    # Варіант 2 (якщо домовимося віддавати словником): прибрати SerializerMethodField
    #   та метод get_skills — тоді DRF віддаватиме сирий словник {"coding": 65} напряму.
    # =========================================================================
    skills = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id",
            "name",
            "specialization",
            "level",
            "skills",
            "expected_salary",
            "is_available",
        ]
        read_only_fields = fields

    def get_skills(self, obj: Candidate) -> list[dict[str, object]]:
        if not isinstance(obj.skills, dict):
            return []
        return [
            {"skill": skill_name, "value": value}
            for skill_name, value in obj.skills.items()
        ]


class HireCandidateSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField(min_value=1)
