from typing import Any
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from django.utils import timezone
from django.db.models import Prefetch, OuterRef

from quiz.paginations import StandardResultsSetPagination
from quiz.filters import CompetitionFilter, NestedCompetitionFilter
from quiz.models import (
    Competition,
    Question,
    UserAnswer,
    UserCompetition,
    Hint,
    HintAchivement,
)
from quiz.permissions import IsEligibleToAnswer
from quiz.serializers import (
    CompetitionSerializer,
    CompetitionCreateSerializer,
    QuestionSerializer,
    UserAnswerSerializer,
    UserCompetitionSerializer,
    HintAchivementSerializer,
    HintSerializer,
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class CompetitionViewList(ListCreateAPIView):
    filter_backends = []
    queryset = Competition.objects.filter(is_active=True).order_by("-created_at")
    pagination_class = StandardResultsSetPagination
    serializer_class = CompetitionSerializer


class UserCompetitionView(ModelViewSet):
    serializer_class = CompetitionCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Competition.objects.filter(user_profile=self.request.user.profile)


class CompetitionView(RetrieveAPIView):
    queryset = Competition.objects.filter(is_active=True)
    serializer_class = CompetitionSerializer


class QuestionView(RetrieveAPIView):
    http_method_names = ["get"]
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()


class EnrollInCompetitionView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [CompetitionFilter]
    queryset = UserCompetition.objects.prefetch_related("usercompetitionhint_set")

    serializer_class = UserCompetitionSerializer

    def perform_create(self, serializer: UserCompetitionSerializer):
        user = self.request.user.profile  # type: ignore
        serializer.save(user_profile=user)

        instance = serializer.instance

        competition: Any = serializer.validated_data.get("competition")

        if competition.participants.count() >= competition.max_participants:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"message": "You have reached the maximum number of participants"},
            )

        if competition.participants.count() >= competition.max_participants:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"message": "You have reached the maximum number of participants"},
            )

        instance.save()

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(  # type: ignore
            f"quiz_list",
            {"type": "increase_enrollment", "data": competition.id},
        )

    def get_queryset(self):
        return self.queryset.filter(user_profile=self.request.user.profile)


class UserAnswerView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsEligibleToAnswer]
    serializer_class = UserAnswerSerializer
    filter_backends = [NestedCompetitionFilter]
    queryset = UserAnswer.objects.all()

    def get_queryset(self):
        return self.queryset.filter(competition__start_at__gte=timezone.now())

    def perform_create(self, serializer):
        serializer.save()


class UserHintsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = HintAchivementSerializer
    queryset = HintAchivement.objects.order_by("is_used")

    def get_queryset(self):
        return self.queryset.filter(user_profile=self.request.user.profile)


class HintsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = HintSerializer
    queryset = Hint.objects.filter(is_active=True)
