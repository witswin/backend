import math
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.manager import BaseManager

from authentication.models import UserProfile
from quiz.constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND
from quiz.models import Competition, UserCompetition


def is_user_eligible_to_participate(
    user_profile: UserProfile | None, competition: Competition
) -> bool:
    if not user_profile:
        return False
    try:
        user_competition = UserCompetition.objects.get(
            user_profile=user_profile, competition=competition
        )
    except UserCompetition.DoesNotExist:
        return False

    if competition.start_at >= timezone.now():
        return True

    has_wrong_answer = user_competition.users_answer.filter(
        selected_choice__is_correct=False
    ).exists()

    if (
        competition.is_active is False
        or competition.is_in_progress is False
        or has_wrong_answer
    ):
        return False

    question_number = user_competition.users_answer.count()

    state = get_quiz_question_state(competition) - 1

    if state > question_number:
        return False

    return True


def get_quiz_question_state(competition: Competition):

    start_at = competition.start_at

    if timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
    else:
        start_at = start_at.astimezone(timezone.get_current_timezone())

    if start_at > timezone.now():
        return 0

    return min(
        math.floor(
            (timezone.now() - start_at).seconds
            / (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
        )
        + 1,
        competition.questions.count(),
    )


def is_competition_finished(competition: Competition):
    start_at = competition.start_at

    if timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
    else:
        start_at = start_at.astimezone(timezone.get_current_timezone())

    if start_at > timezone.now():
        return False

    return (
        math.floor(
            (timezone.now() - start_at).seconds
            / (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
        )
        + 1
        > competition.questions.count()
    )


def get_round_participants(
    competition: Competition,
    total_participants: BaseManager[UserCompetition],
    question_number: int,
) -> int:
    if question_number <= 0:
        return total_participants.count()

    total_questions = competition.questions.count()
    question_number = min(question_number, total_questions)

    if competition.is_finished:
        question_number += 1

    return (
        total_participants.annotate(
            correct_answer_count=Count(
                "users_answer",
                filter=Q(users_answer__selected_choice__is_correct=True),
            ),
        )
        .filter(
            correct_answer_count__gte=question_number - 1,
            # incorrect_answer_count=0,
        )
        .distinct()
        .count()
    )


def get_previous_round_losses(
    competition: Competition,
    total_participants: BaseManager[UserCompetition],
    question_number: int,
):

    if competition.can_be_shown:
        participating_count = get_round_participants(
            competition, total_participants, question_number
        )
    else:
        participating_count = total_participants.count()

    return max(
        get_round_participants(competition, total_participants, question_number - 1)
        - participating_count,
        0,
    )
