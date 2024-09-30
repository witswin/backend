from django.urls import path
from authentication.views import AuthenticateView, GetProfileView
from rest_framework.routers import DefaultRouter


router = DefaultRouter()


urlpatterns = [
    path("info/", GetProfileView.as_view()),
    path("statistics/", AuthenticateView.as_view()),
    path("authenticate/", AuthenticateView.as_view()),
] + router.urls
