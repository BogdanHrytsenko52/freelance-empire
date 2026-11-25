from django.urls import path

from .views import TransactionListView

app_name = "finances"

urlpatterns = [
    path("", TransactionListView.as_view(), name="transaction-list"),
]
