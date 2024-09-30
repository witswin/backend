from django.urls import path
from rest_framework.routers import DefaultRouter

from quiz.views import (
    CompetitionView,
    CompetitionViewList,
    EnrollInCompetitionView,
    QuestionView,
    UserAnswerView,
    UserCompetitionView,
)


router = DefaultRouter()

router.register("dashboard/competitions", UserCompetitionView, "user-competition")

urlpatterns = [
    path("competitions/", CompetitionViewList.as_view(), name="competition-list"),
    path("competitions/<int:pk>/", CompetitionView.as_view(), name="competition"),
    path("questions/<int:pk>/", QuestionView.as_view(), name="question"),
    path(
        "competitions/enroll/",
        EnrollInCompetitionView.as_view(),
        name="enroll-competition",
    ),
    path(
        "competitions/submit-answer/",
        UserAnswerView.as_view(),
        name="user-competition-answers",
    ),
] + router.urls


app_name = "QUIZ"
