from django.urls import path
from .views import GeneralStatsView


urlpatterns = [path("total/", GeneralStatsView.as_view())]
