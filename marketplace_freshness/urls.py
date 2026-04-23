from django.urls import path

from .views import freshness_index

app_name = "marketplace_freshness"

urlpatterns = [
    path("", freshness_index, name="index"),
]
