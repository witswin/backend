from typing import Any
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from authentication.models import UserProfile
from quiz.models import Choice, Competition, Question, UserAnswer, UserCompetition
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from quiz.constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND
from quiz.utils import (
    get_previous_round_losses,
    get_quiz_question_state,
    get_round_participants,
    is_competition_finished,
    is_user_eligible_to_participate,
)

User = get_user_model()


CORRECT_CHOICE_INDEX = 3
HINT_CHOICES = [0, 2]
PRIZE_AMOUNT = 20000


class BaseQuizTestUtils:
    questions_list: list[Question] = []

    correct_choice_index = CORRECT_CHOICE_INDEX
    hint_choices = HINT_CHOICES

    competition: Competition

    user_profile: UserProfile

    token: str

    def create_answer(
        self, enrollment: UserCompetition, question: Question, choice_index
    ):
        selected_choice = Choice.objects.filter(question=question).order_by("id")[
            choice_index
        ]

        return UserAnswer.objects.create(
            user_competition=enrollment,
            question=question,
            selected_choice=selected_choice,
        )

    def enroll_user(self, user: UserProfile, competition: Competition):
        return UserCompetition.objects.create(
            competition=competition,
            user_profile=user,
            hint_count=competition.hint_count,
        )

    def get_competition_participants(self):
        return UserCompetition.objects.filter(competition=self.competition)

    def create_test_user(self):
        user = User.objects.create_user("test_user")
        profile = UserProfile.objects.create(
            user=user, wallet_address="0x623123123", username="test_user"
        )

        self.user_profile = profile

        self.token = Token.objects.get_or_create(user=user)[0].key

    def create_sample_question(self, question_number: int):
        question = Question.objects.create(
            competition=self.competition,
            text=f"Sample question number {question_number}",
            number=question_number,
        )

        for i in range(4):
            is_choice_correct = i == self.correct_choice_index

            choice = Choice.objects.create(
                question=question,
                is_correct=is_choice_correct,
                text=f"Sample Answer [{i}]",
                is_hinted_choice=bool(i in self.hint_choices),
            )

        return question

    def update_quiz_start_at(self, start_at):
        self.competition.start_at = start_at
        self.competition.save(update_fields=["start_at"])


class QuizRestfulTestCase(APITestCase, BaseQuizTestUtils):
    questions_list: list[Question] = []

    correct_choice_index = CORRECT_CHOICE_INDEX
    hint_choices = HINT_CHOICES

    competition: Competition

    user_profile: UserProfile

    token: str

    def reverse_url(self, path, *args, **kwargs):
        return reverse(f"{self.app_name}:{path}", args=args, kwargs=kwargs)

    def setUp(self):
        self.app_name = "QUIZ"
        self.create_test_user()
        self.competition = Competition.objects.create(
            title="Test Competition",
            start_at=timezone.now() - timezone.timedelta(minutes=5),
            user_profile=self.user_profile,
            prize_amount=PRIZE_AMOUNT,
            chain_id=10,
            token_decimals=6,
            token="USDC",
            token_address="0x",
            email_url="test@test.test",
        )

        self.questions_list = [
            self.create_sample_question(1),
            self.create_sample_question(2),
            self.create_sample_question(3),
            self.create_sample_question(4),
        ]

    def update_quiz_start_at(self, start_at):
        self.competition.start_at = start_at
        self.competition.save(update_fields=["start_at"])

    def get_authenticated_headers(self):
        return {"Authorization": f"TOKEN {self.token}"}

    def test_competition_status(self):
        self.assertFalse(
            self.competition.is_in_progress, "Competition is not in progress"
        )
        self.assertTrue(self.competition.can_be_shown, "Competition can be shown")
        self.assertTrue(
            is_competition_finished(self.competition), "Competition is finished"
        )

    def test_competition_list(self):
        res = self.client.get(self.reverse_url("competition-list"))

        self.assertEqual(res.status_code, 200)

        data = res.json()

        self.assertEqual(data["count"], 1, "Only 1 competition")
        self.assertEqual(
            data["results"][0]["id"],
            self.competition.pk,
            "competition Primary keys matches",
        )
        self.assertEqual(
            data["results"][0]["participantsCount"],
            0,
            "No participants on recently created competition",
        )
        self.assertEqual(
            data["results"][0]["prizeAmount"],
            float(self.competition.prize_amount),
            "Prizes on competition must match",
        )

    def test_enrollment_prevent_when_finished(self):
        enroll_res = self.client.post(
            self.reverse_url("enroll-competition"),
            data={"competition": self.competition.pk},
            headers=self.get_authenticated_headers(),
        )

        self.assertEqual(
            enroll_res.status_code, 400, "Not Allowed to enroll when quiz is finished"
        )

    def test_user_enroll(self):

        self.update_quiz_start_at(timezone.now() + timezone.timedelta(minutes=5))

        enroll_res = self.client.post(
            self.reverse_url("enroll-competition"),
            data={"competition": self.competition.pk},
            headers=self.get_authenticated_headers(),
        )

        self.assertEqual(
            enroll_res.status_code, 201, "Allow to enroll when the quiz is not started"
        )

        res = self.client.get(self.reverse_url("competition-list"))
        data = res.json()
        self.assertEqual(
            data["results"][0]["participantsCount"],
            1,
            "Added user to the participants count",
        )

    def test_competition_is_active_false(self):
        self.competition.is_active = False

        self.competition.save(update_fields=["is_active"])
        res = self.client.get(self.reverse_url("competition-list"))
        data = res.json()
        self.assertEqual(data["count"], 0, "Remove the quiz if is_active is False")

    def test_questions_state_when_finished(self):
        self.assertEqual(
            get_quiz_question_state(self.competition),
            self.competition.questions.count(),
            "The quiz is finished so we are in the last question state",
        )

    def test_questions_first_state(self):

        self.update_quiz_start_at(
            timezone.now() - timezone.timedelta(seconds=ANSWER_TIME_SECOND - 2)
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 1, "We are in question 1"
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND - 0.5
            )
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 1, "We are in question 1"
        )

    def test_questions_seconds_state(self):
        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND
            )
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 2, "We are in question 2"
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND * 2 + REST_BETWEEN_EACH_QUESTION_SECOND
            )
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 2, "We are in question 2"
        )

    def test_user_eligibily(self):
        user_enrollment = self.enroll_user(self.user_profile, self.competition)

        self.update_quiz_start_at(timezone.now() - timezone.timedelta(seconds=5))

        is_eligible = is_user_eligible_to_participate(
            self.user_profile, self.competition
        )

        self.assertTrue(
            is_eligible, "User should be eligible to participate in the quiz"
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND
            )
        )

        is_eligible = is_user_eligible_to_participate(
            self.user_profile, self.competition
        )

        self.assertFalse(
            is_eligible, "User should NOT be eligible to participate in the quiz"
        )


class QuizUtilsTestCase(TestCase, BaseQuizTestUtils):

    def setUp(self):
        self.app_name = "QUIZ"
        self.create_test_user()
        self.competition = Competition.objects.create(
            title="Test Competition",
            start_at=timezone.now() - timezone.timedelta(minutes=5),
            user_profile=self.user_profile,
            prize_amount=PRIZE_AMOUNT,
            chain_id=10,
            token_decimals=6,
            token="USDC",
            token_address="0x",
            email_url="test@test.test",
        )

        self.questions_list = [
            self.create_sample_question(1),
            self.create_sample_question(2),
            self.create_sample_question(3),
            self.create_sample_question(4),
            self.create_sample_question(5),
            self.create_sample_question(6),
            self.create_sample_question(7),
            self.create_sample_question(8),
        ]

    def create_user_profile(self, name="test_user1", address="0x1"):
        user = User.objects.create_user(name)
        profile = UserProfile.objects.create(
            user=user, wallet_address=address, username=name
        )

        return profile

    def enroll_user(self, user: UserProfile, competition: Competition):
        return UserCompetition.objects.create(
            competition=competition,
            user_profile=user,
            hint_count=competition.hint_count,
        )

    def test_enroll_stats(self):
        users = [
            self.create_user_profile("ali", "0xFD"),
            self.create_user_profile("mamad", "0x862"),
            self.create_user_profile("mamadreza", "0x862FA"),
        ]

        user_enrolls = []

        for user in users:
            user_enrolls.append(self.enroll_user(user, self.competition))

        self.update_quiz_start_at(
            timezone.now() - timezone.timedelta(seconds=ANSWER_TIME_SECOND + 1)
        )

        question: Any = self.competition.questions.order_by("number").first()

        for user_enroll in user_enrolls[:2]:
            answer = self.create_answer(
                user_enroll,
                question,
                CORRECT_CHOICE_INDEX,
            )

        question_state = get_quiz_question_state(self.competition)

        participants_q1 = get_round_participants(
            self.competition, self.get_competition_participants(), question_state + 1
        )

        losers = get_previous_round_losses(
            self.competition, self.get_competition_participants(), question_state + 1
        )

        self.assertEqual(losers, 1, "One user didn't answer")
        self.assertEqual(participants_q1, 2, "Two users answered correctly")

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND
                + REST_BETWEEN_EACH_QUESTION_SECOND
                + ANSWER_TIME_SECOND
                + 1
            )
        )

        question: Any = self.competition.questions.order_by("number")[1]

        for user_enroll in user_enrolls[:2]:
            answer = self.create_answer(
                user_enroll,
                question,
                CORRECT_CHOICE_INDEX,
            )

        question_state = get_quiz_question_state(self.competition)

        participants_q1 = get_round_participants(
            self.competition, self.get_competition_participants(), question_state + 1
        )

        losers = get_previous_round_losses(
            self.competition, self.get_competition_participants(), question_state + 1
        )

        self.assertEqual(losers, 0, "No losers")
        self.assertEqual(participants_q1, 2, "Two users answered correctly")

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=(ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND) * 2
                + ANSWER_TIME_SECOND
                + 1
            )
        )

        question: Any = self.competition.questions.order_by("number")[2]

        answer = self.create_answer(
            user_enrolls[0],
            question,
            CORRECT_CHOICE_INDEX,
        )

        question_state = get_quiz_question_state(self.competition)

        participants_q1 = get_round_participants(
            self.competition, self.get_competition_participants(), question_state + 1
        )

        losers = get_previous_round_losses(
            self.competition, self.get_competition_participants(), question_state + 1
        )

        self.assertEqual(losers, 1, "One loser")
        self.assertEqual(participants_q1, 1, "One user answered correctly")

    def test_enroll_stats_first_question(self):
        user1 = self.create_user_profile("ali", "0xFD")
        user2 = self.create_user_profile("mamad", "0x862")
        user3 = self.create_user_profile("mamadreza", "0x862FA")

        user_enroll1 = self.enroll_user(user1, self.competition)
        user_enroll2 = self.enroll_user(user2, self.competition)
        user_enroll3 = self.enroll_user(user3, self.competition)

        self.update_quiz_start_at(timezone.now())

        question_state = get_quiz_question_state(self.competition)

        self.assertEqual(question_state, 1, "Must be at first question")

        participants = get_round_participants(
            self.competition, self.get_competition_participants(), question_state
        )

        self.assertEqual(participants, 3, "3 Participants must be active")

        self.assertTrue(
            is_user_eligible_to_participate(user1, self.competition),
            "User 1 must be eligible",
        )

        self.assertTrue(
            is_user_eligible_to_participate(user2, self.competition),
            "User 2 must be eligible",
        )

        self.assertTrue(
            is_user_eligible_to_participate(user3, self.competition),
            "User 3 must be eligible",
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND
            )
        )

        question_state = get_quiz_question_state(self.competition)

        participants_q1 = get_round_participants(
            self.competition, self.get_competition_participants(), question_state
        )

        losers = get_previous_round_losses(
            self.competition, self.get_competition_participants(), question_state
        )

        self.assertEqual(participants_q1, 0, "No participants answered")
        self.assertEqual(losers, 3, "All players lost")

        question: Any = self.competition.questions.order_by("number").first()

        answer = self.create_answer(
            user_enroll1,
            question,
            CORRECT_CHOICE_INDEX,
        )

        self.assertTrue(
            answer.selected_choice.is_correct, "Must have selected the correct answer"
        )

        answer = self.create_answer(user_enroll2, question, 0)

        self.assertFalse(
            answer.selected_choice.is_correct, "Must have selected the WRONG answer"
        )

        participants_q1 = get_round_participants(
            self.competition, self.get_competition_participants(), question_state
        )
        losers = get_previous_round_losses(
            self.competition, self.get_competition_participants(), question_state
        )

        self.assertEqual(participants_q1, 1, "One participants answered")
        self.assertEqual(losers, 2, "2 Players Lost")

    def test_enroll_stats_last_question(self):
        user1 = self.create_user_profile("ali", "0xFD")
        user2 = self.create_user_profile("mamad", "0x862")
        user3 = self.create_user_profile("mamadreza", "0x862FA")

        user_enroll1 = self.enroll_user(user1, self.competition)
        user_enroll2 = self.enroll_user(user2, self.competition)
        user_enroll3 = self.enroll_user(user3, self.competition)

        for question in self.competition.questions.all():
            answer = self.create_answer(
                user_enroll1,
                question,
                CORRECT_CHOICE_INDEX,
            )

            answer2 = self.create_answer(user_enroll2, question, 0)

            if question.number < 3:
                answer3 = self.create_answer(
                    user_enroll3, question, CORRECT_CHOICE_INDEX
                )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=(
                    (REST_BETWEEN_EACH_QUESTION_SECOND + ANSWER_TIME_SECOND)
                    * self.competition.questions.count()
                )
                - REST_BETWEEN_EACH_QUESTION_SECOND
                - 3
            )
        )

        question_state = get_quiz_question_state(self.competition)

        self.assertEqual(
            question_state,
            self.competition.questions.count(),
            "Must be at last question",
        )

        participants = get_round_participants(
            self.competition, self.get_competition_participants(), question_state
        )

        losers = get_previous_round_losses(
            self.competition, self.get_competition_participants(), question_state
        )

        self.assertEqual(participants, 1, "One participants answered correctly")
        self.assertEqual(losers, 0, "No player lost at last question")

        self.assertFalse(
            is_user_eligible_to_participate(user2, self.competition),
            "User 2 is not allowed to participate",
        )
        self.assertFalse(
            is_user_eligible_to_participate(user3, self.competition),
            "User 3 is not allowed to participate",
        )

        self.assertTrue(
            is_user_eligible_to_participate(user1, self.competition),
            "User 1 is allowed to participate",
        )

    def test_enroll_last_question_wrong(self):
        user1 = self.create_user_profile("ali", "0xFD")
        user2 = self.create_user_profile("mamad", "0x862")
        user3 = self.create_user_profile("mamadreza", "0x862FA")

        user_enroll1 = self.enroll_user(user1, self.competition)
        user_enroll2 = self.enroll_user(user2, self.competition)

        questions_list = list(self.competition.questions.all())
        for question in questions_list[:-1]:
            answer = self.create_answer(
                user_enroll1,
                question,
                CORRECT_CHOICE_INDEX,
            )

        answer = self.create_answer(
            user_enroll1,
            questions_list[-1],
            0,
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=(
                    (REST_BETWEEN_EACH_QUESTION_SECOND + ANSWER_TIME_SECOND)
                    * self.competition.questions.count()
                )
                + 3
            )
        )

        question_state = get_quiz_question_state(self.competition)

        self.assertEqual(
            question_state,
            self.competition.questions.count(),
            "Must be at last question",
        )

        participants = get_round_participants(
            self.competition, self.get_competition_participants(), question_state
        )

        print(question_state)

        losers = get_previous_round_losses(
            self.competition, self.get_competition_participants(), question_state
        )
        self.assertEqual(participants, 0, "All answered wrong")
        self.assertEqual(losers, 1, "One player lost at last question")


class QuizConsumerTestCase(TestCase):

    def setUp(self):
        pass

    async def test_user_stats(self):
        pass
