from django.urls import path

from finances.views import CompanyFinanceView

from .views import CompanyCreateView, MyCompanyView

app_name = "companies"

urlpatterns = [
    path("", CompanyCreateView.as_view(), name="company-create"),
    path("me/", MyCompanyView.as_view(), name="company-me"),
    path("me/finance/", CompanyFinanceView.as_view(), name="company-finance"),
]
