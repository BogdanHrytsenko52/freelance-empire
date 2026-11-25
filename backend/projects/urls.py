from django.urls import path

from .views import (
    ProjectAssignView,
    ProjectDetailView,
    ProjectListView,
    ProjectSubmitView,
    ProjectUnassignView,
)

app_name = "projects"

urlpatterns = [
    path("", ProjectListView.as_view(), name="project-list"),
    path("<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("<int:pk>/assign/", ProjectAssignView.as_view(), name="project-assign"),
    path("<int:pk>/unassign/", ProjectUnassignView.as_view(), name="project-unassign"),
    path("<int:pk>/submit/", ProjectSubmitView.as_view(), name="project-submit"),
]
