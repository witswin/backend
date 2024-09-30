from datetime import timedelta
import math
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.db.models import F, Count
from authentication.models import UserProfile
from .constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND
from core.fields import BigNumField
from cloudflare_images.field import CloudflareImagesField


class Sponsor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    link = models.URLField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = CloudflareImagesField(blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class CompetitionManager(models.Manager):
    def with_question_count(self):
        return self.annotate(question_count=Count("questions"))

    @property
    def not_started(self):
        return self.filter(start_at__gt=timezone.now())

    @property
    def finished(self):
        return self.with_question_count().filter(
            start_at__lt=timezone.now()
            - timezone.timedelta(
                seconds=F("questions__count")
                * (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
            )
        )

    @property
    def started(self):
        return self.filter(start_at__lte=timezone.now())

    @property
    def in_progress(self):
        # Competitions that have started but not yet finished
        return (
            self.with_question_count()
            .filter(start_at__lte=timezone.now())
            .filter(
                start_at__gt=timezone.now()
                - timezone.timedelta(
                    seconds=F("question_count")
                    * (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
                )
            )
        )


class Competition(models.Model):
    title = models.CharField(max_length=255)
    sponsors = models.ManyToManyField(
        Sponsor,
        related_name="competitions",
        blank=True,
    )
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, blank=True)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_at = models.DateTimeField(null=False, blank=False)
    prize_amount = BigNumField(null=False, blank=False)
    chain_id = models.IntegerField()
    token_decimals = models.PositiveIntegerField(default=18)
    token = models.CharField(max_length=100)
    token_address = models.CharField(max_length=255)
    discord_url = models.URLField(max_length=255, null=True, blank=True)
    twitter_url = models.URLField(max_length=255, null=True, blank=True)
    email_url = models.EmailField(max_length=255)
    telegram_url = models.URLField(max_length=255, null=True, blank=True)
    token_image = CloudflareImagesField(blank=True, null=True)
    image = CloudflareImagesField(blank=True, null=True)
    shuffle_answers = models.BooleanField(default=False)
    split_prize = models.BooleanField(default=True)

    participants = models.ManyToManyField(
        UserProfile,
        through="UserCompetition",
        related_name="participated_competitions",
    )

    tx_hash = models.CharField(max_length=1000, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    objects: CompetitionManager = CompetitionManager()
    questions: models.QuerySet["Question"]
    hint_count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user_profile} - {self.title}"

    @property
    def is_in_progress(self):
        return self.can_be_shown and (
            self.start_at
            + timedelta(
                seconds=(
                    self.questions.count()
                    * (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
                    - REST_BETWEEN_EACH_QUESTION_SECOND
                )
            )
            >= timezone.now()
        )

    @property
    def can_be_shown(self):
        return self.start_at <= timezone.now()

    @property
    def is_finished(self):
        return (
            not self.is_in_progress
            and self.start_at
            + timezone.timedelta(
                seconds=self.questions.count()
                * (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
            )
            <= timezone.now()
        )


class UserCompetitionManager(models.Manager):
    def is_eligible(self, competition: Competition):
        if not competition.is_active:
            return self.none()

        state = math.floor(
            (timezone.now() - competition.start_at).seconds
            / (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
        )

        return self.annotate().filter(
            competition=competition,
            user_answer__selected_choice__is_correct=True,
            user_answer__gte=state,
        )


class UserCompetition(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    is_winner = models.BooleanField(default=False)
    amount_won = BigNumField(default=0)
    hint_count = models.PositiveIntegerField(default=0)
    tx_hash = models.CharField(max_length=1000, blank=True)
    users_answer: models.QuerySet

    class Meta:
        unique_together = ("user_profile", "competition")

    def __str__(self):
        return f"{self.user_profile} - {self.competition.title}"


class QuestionManager(models.Manager):
    @property
    def can_be_shown(self):
        return self.filter(competition__start_at__lte=timezone.now())


class Question(models.Model):
    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="questions"
    )
    number = models.IntegerField(
        null=False, blank=False, validators=[MinValueValidator(1)]
    )
    text = models.TextField()

    choices: models.QuerySet

    users_answer: models.QuerySet

    @property
    def can_be_shown(self):
        return (
            self.competition.start_at
            + timezone.timedelta(
                seconds=(self.number - 1)
                * (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
            )
            <= timezone.now()
        )

    @property
    def answer_can_be_shown(self):
        answer_time = ANSWER_TIME_SECOND - 2

        seconds = (self.number - 1) * (
            ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND
        ) + answer_time

        return (
            self.competition.start_at + timezone.timedelta(seconds=seconds)
        ) <= timezone.now()

    objects: QuestionManager = QuestionManager()

    def __str__(self):
        return f"{self.competition.title} - {self.number} - {self.text}"

    class Meta:
        unique_together = ("competition", "number")


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    is_hinted_choice = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class UserAnswer(models.Model):
    user_competition = models.ForeignKey(
        UserCompetition,
        on_delete=models.CASCADE,
        related_name="users_answer",
        null=False,
        blank=False,
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="users_answer",
        null=False,
        blank=False,
    )
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        related_name="users_answer",
        null=False,
        blank=False,
    )

    class Meta:
        unique_together = ("user_competition", "question")

    def __str__(self):
        return (
            f"{self.user_competition.user_profile} "
            f"- {self.user_competition.competition.title} - {self.question.number}"
        )
