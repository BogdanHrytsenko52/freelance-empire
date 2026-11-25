from django.urls import path

from .views import ActiveEventListView, EventChooseView, EventHistoryListView

app_name = "events"

urlpatterns = [
    path("", ActiveEventListView.as_view(), name="event-list"),
    path("history/", EventHistoryListView.as_view(), name="event-history"),
    path("<int:pk>/choose/", EventChooseView.as_view(), name="event-choose"),
]
