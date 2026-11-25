from django.urls import path

from .views import (
    CandidateListView,
    EmployeeListView,
    FireEmployeeView,
    HireCandidateView,
)

app_name = "employees"

urlpatterns = [
    path("", EmployeeListView.as_view(), name="employee-list"),
    path("candidates/", CandidateListView.as_view(), name="candidate-list"),
    path("hire/", HireCandidateView.as_view(), name="employee-hire"),
    path("<int:pk>/fire/", FireEmployeeView.as_view(), name="employee-fire"),
]
