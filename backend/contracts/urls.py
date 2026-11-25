from django.urls import path

from .views import ContractAcceptView, ContractDetailView, ContractListView

app_name = "contracts"

urlpatterns = [
    path("", ContractListView.as_view(), name="contract-list"),
    path("<int:pk>/", ContractDetailView.as_view(), name="contract-detail"),
    path("<int:pk>/accept/", ContractAcceptView.as_view(), name="contract-accept"),
    # =========================================================================
    # TODO / УЗГОДЖЕННЯ (AI-чат Богдана):
    # Маршрут GET/POST /api/contracts/<int:pk>/chat/ реалізує Богдан (ai_service/).
    # Його можна буде підключити або тут, або окремим рядком у config/urls.py.
    # =========================================================================
]
