from django.urls import path
from authentication.views import AuthenticateView, GetProfileView, VerifyWalletView, createMessageView
from rest_framework.routers import DefaultRouter


router = DefaultRouter()


urlpatterns = [
    path("info/", GetProfileView.as_view()),
    path("statistics/", AuthenticateView.as_view()),
    path("authenticate/", AuthenticateView.as_view()),
    path("verify-wallet/", VerifyWalletView.as_view(), name='verify-wallet'),
    path("create-message/", createMessageView.as_view(), name='create-message'),
] + router.urls
