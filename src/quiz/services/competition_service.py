from typing import Any
from django.core.exceptions import ObjectDoesNotExist
from quiz.models import Competition, UserCompetition, UserAnswer, Question
from authentication.models import UserProfile
from django.core.serializers.json import DjangoJSONEncoder
from quiz.serializers import UserAnswerSerializer, QuestionSerializer
from channels.layers import get_channel_layer
from django.utils import timezone
from asgiref.sync import async_to_sync
from quiz.utils import (
    is_user_eligible_to_participate,
    get_quiz_question_state,
    get_round_participants,
    get_previous_round_losses,
)
from django.core.cache import cache

from collections import Counter

import json


class CompetitionService:
    def __init__(self, competition_pk) -> None:
        self.competition = self._get_competition(competition_pk)

    def _get_competition(self, competition_pk) -> Competition:
        try:
            return Competition.objects.get(pk=competition_pk)
        except ObjectDoesNotExist:
            raise ValueError(f"Competition with id {competition_pk} does not exist.")

    def resolve_hint(
        self, user_competition: UserCompetition, question_id: int, hint_id: int
    ):
        hint_service = CompetitionHintService(user_competition)

        return hint_service.resolve_hint(question_id, hint_id)

    def get_user_competition(self, profile: UserProfile) -> UserCompetition:
        return UserCompetition.objects.filter(
            user_profile=profile, competition=self.competition
        ).first()

    def _get_answer_diff(self, answers_count: int) -> int:
        question_state = get_quiz_question_state(self.competition)
        return max(0, question_state - 1 - answers_count)

    def _get_missed_answers(self, user_competition: UserCompetition, diff: int) -> list:
        missed_answers = []

        for i in range(diff):
            question_number = (
                UserAnswer.objects.filter(user_competition=user_competition).count()
                + i
                + 1
            )
            question = Question.objects.get(
                number=question_number, competition=self.competition
            )
            answer = UserAnswer(
                user_competition=user_competition, question=question, id=-1
            )
            missed_answers.append(answer)
        return missed_answers

    def send_user_answers(
        self, profile: UserProfile, user_competition: UserCompetition
    ):
        answers = UserAnswer.objects.filter(
            user_competition__competition=self.competition,
            user_competition__user_profile=profile,
        )

        missed_answers = self._get_missed_answers(
            user_competition, self._get_answer_diff(answers.count())
        )

        all_answers = list(answers) + missed_answers

        serialized_answers = UserAnswerSerializer(all_answers, many=True)

        return [
            {
                **answer,
                "selected_choice": answer.get(
                    "selected_choice", {"is_correct": False, "id": None}
                ),
            }
            for answer in serialized_answers.data
        ]

    def calculate_quiz_winners(self):
        return list(
            UserCompetition.objects.filter(is_winner=True, competition=self.competition)
            .values("user_profile__wallet_address", "tx_hash")
            .distinct()
        )

    def get_question(self, number: int, user_profile=None):
        instance = Question.objects.can_be_shown.filter(
            competition=self.competition, number=number
        ).first()

        data: Any = QuestionSerializer(instance=instance).data

        return {
            "question": {
                **data,
                "is_eligible": user_profile
                and is_user_eligible_to_participate(user_profile, self.competition),
            },
            "type": "new_question",
        }

    def get_quiz_stats(self, user_competition: UserCompetition, state=None):
        prize_to_win = self.competition.prize_amount
        users_participated = UserCompetition.objects.filter(
            competition=self.competition
        )

        question_number = state or get_quiz_question_state(self.competition)

        participating_count = get_round_participants(
            self.competition, users_participated, question_number
        )

        return {
            "type": "quiz_stats",
            "data": {
                "users_participating": participating_count,
                "prize_to_win": (
                    prize_to_win
                    if self.competition.split_prize is False
                    else (
                        prize_to_win / participating_count
                        if participating_count > 0
                        else 0
                    )
                ),
                "total_participants_count": self.competition.participants.count(),
                "questions_count": self.competition.questions.count(),
                "hint_count": (user_competition.hint_count if user_competition else 0),
                "previous_round_losses": get_previous_round_losses(
                    self.competition, users_participated, question_number
                ),
            },
        }

    def save_user_answer(
        self,
        user_competition: UserCompetition,
        question_id: int,
        selected_choice_id: int,
    ):
        question: Question = Question.objects.can_be_shown.get(pk=question_id)
        answers = cache.get(f"question_{question.pk}_answers", {})

        answers[user_competition.pk] = selected_choice_id

        cache.set(f"question_{question.pk}_answers", answers)

        return {
            "selected_choice_id": selected_choice_id,
        }

    def get_current_question(self, user_profile: UserProfile = None):
        competition_time = self.competition.start_at

        now = timezone.now()

        if now < competition_time:
            return None

        state = get_quiz_question_state(competition=self.competition)

        return self.get_question(state, user_profile)


class CompetitionHintService:
    def __init__(self, user_competition: UserCompetition):
        self.user_competition = user_competition

    def get_hints(self):
        return self.user_competition.registered_hints.all()

    def get_hint(self, pk):
        return self.user_competition.registered_hints.get(pk=pk)

    def resolve_hint(self, question_id: int, hint_id: int):
        if (
            self.user_competition.usercompetitionhint_set.filter(
                hint_id=hint_id, is_used=False
            ).exists()
            is False
        ):
            raise ValueError("No hints left")

        hint = self.user_competition.usercompetitionhint_set.filter(
            hint_id=hint_id, is_used=False
        ).first()

        hint.question = Question.objects.get(pk=question_id)

        hint.is_used = True
        hint.save()

        if hint.hint.hint_type == "stats":
            return self.resolve_stats_hint(question_id)

        elif hint.hint.hint_type == "fifty":
            return self.resolve_fifty_hint(question_id)

    def resolve_fifty_hint(self, question_id: int):
        question: Question = Question.objects.can_be_shown.filter(
            pk=question_id, competition=self.user_competition.competition
        ).first()

        return list(
            question.choices.filter(is_hinted_choice=True).values_list("pk", flat=True)
        )

    def resolve_stats_hint(self, question_id: int):
        answers = cache.get(f"question_{question_id}_answers", {})

        total_answers = len(answers)

        answer_percentages = {}

        answer_counts = Counter(answers.values())

        for answer_id, count in answer_counts.items():
            percentage = (count / total_answers) * 100
            answer_percentages[answer_id] = round(percentage, 2)

        return answer_percentages


class CompetitionBroadcaster:
    def __init__(self):
        self.channel_layer = get_channel_layer()

    def broadcast_competition_deleted(self, competition: Competition):
        async_to_sync(self.channel_layer.group_send)(  # type: ignore
            f"quiz_list",
            {"type": "delete_competition", "data": competition.pk},
        )

    def broadcast_competition_updated(self, competition: Competition):
        async_to_sync(self.channel_layer.group_send)(  # type: ignore
            f"quiz_list",
            {"type": "update_competition_data", "data": competition.pk},
        )

    def broadcast_competition_stats(self, competition: Competition, state=None):
        async_to_sync(self.channel_layer.group_send)(  # type: ignore
            f"quiz_{competition.pk}",
            {"type": "send_quiz_stats", "data": state},
        )

    def broadcast_question(self, competition: Competition, question: Question):
        data = QuestionSerializer(instance=question).data

        async_to_sync(self.channel_layer.group_send)(  # type: ignore
            f"quiz_{competition.pk}",
            {"type": "send_question", "data": json.dumps(data, cls=DjangoJSONEncoder)},
        )

    def broadcast_competition_finished(self, competition: Competition):
        async_to_sync(self.channel_layer.group_send)(  # type: ignore
            f"quiz_{competition.pk}",
            {"type": "finish_quiz", "data": {}},
        )

    def broadcast_correct_answer(
        self,
        competition: Competition,
        answer_id: int,
        question_id: int,
        question_number: int,
    ):
        async_to_sync(self.channel_layer.group_send)(  # type: ignore
            f"quiz_{competition.pk}",
            {
                "type": "send_correct_answer",
                "data": {
                    "answer_id": answer_id,
                    "question_number": question_number,
                    "question_id": question_id,
                },
            },
        )
