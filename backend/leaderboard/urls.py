from django.urls import path

from .views import LeaderboardListView

app_name = "leaderboard"

urlpatterns = [
    path("", LeaderboardListView.as_view(), name="leaderboard-list"),
]
