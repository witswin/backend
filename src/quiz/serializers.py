import random

from rest_framework import serializers
from core.fields import CurrentUserProfileDefault
from quiz.models import (
    Choice,
    Competition,
    Question,
    Sponsor,
    UserAnswer,
    UserCompetition,
    Hint,
    HintAchivement,
)
from quiz.utils import is_user_eligible_to_participate


class SponsorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        fields = "__all__"


class SmallQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ("pk", "number")


class HintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hint
        fields = "__all__"


class HintAchivementSerializer(serializers.ModelSerializer):
    class Meta:
        model = HintAchivement
        fields = ("pk", "is_used", "hint", "used_at", "created_at")


class CompetitionSerializer(serializers.ModelSerializer):
    questions = SmallQuestionSerializer(many=True, read_only=True)
    sponsors = SponsorSerializer(many=True, read_only=True)
    participants_count = serializers.IntegerField(
        source="participants.count", read_only=True
    )
    user_profile = CurrentUserProfileDefault()
    built_in_hints = HintSerializer(many=True, read_only=True)

    class Meta:
        model = Competition
        exclude = ("participants",)


class ChoiceSerializer(serializers.ModelSerializer):
    is_correct = serializers.SerializerMethodField()

    class Meta:
        model = Choice
        exclude = ["is_hinted_choice"]

    def get_is_correct(self, choice: Choice):
        if (
            self.context.get("include_is_correct", False)
            or choice.question.answer_can_be_shown
        ):
            return choice.is_correct
        return None


class ChoiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        exclude = ("question",)


class QuestionSerializer(serializers.ModelSerializer):
    choices = serializers.SerializerMethodField()
    remain_participants_count = serializers.SerializerMethodField(read_only=True)
    total_participants_count = serializers.SerializerMethodField(read_only=True)
    amount_won_per_user = serializers.SerializerMethodField(read_only=True)
    is_eligible = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Question
        fields = "__all__"

    def get_choices(self, obj: Question):
        choices_data = ChoiceSerializer(obj.choices.all(), many=True).data
        if obj.competition.shuffle_answers:
            random.shuffle(choices_data)
        return choices_data

    def get_is_eligible(self, ques: Question):
        if self.context.get("request"):
            try:
                user_profile = self.context.get("request").user.profile  # type: ignore
            except AttributeError:
                return False
        else:
            user_profile = self.context.get("profile")

        return is_user_eligible_to_participate(user_profile, ques.competition)

    def get_remain_participants_count(self, ques: Question):
        users_answered_correct = ques.users_answer.filter(
            selected_choice__is_correct=True
        ).distinct("user_competition__pk")

        return users_answered_correct.count()

    def get_total_participants_count(self, ques: Question):
        return ques.competition.participants.count()

    def get_amount_won_per_user(self, ques: Question):
        prize_amount = ques.competition.prize_amount
        remain_participants_count = self.get_remain_participants_count(ques)

        try:
            prize_amount_per_user = prize_amount / remain_participants_count
            return prize_amount_per_user
        except ZeroDivisionError:
            if ques.competition.is_active and ques.competition.can_be_shown:
                return prize_amount
        except TypeError:
            if ques.competition.is_active and ques.competition.can_be_shown:
                remain_participants_count = self.get_total_participants_count(ques)

                return prize_amount / remain_participants_count


class QuestionCreateSerializer(serializers.ModelSerializer):
    choices = ChoiceCreateSerializer(many=True)

    class Meta:
        model = Question
        exclude = ("competition",)


class CompetitionField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        pk = super(CompetitionField, self).to_representation(value)
        if self.pk_field is not None:
            return self.pk_field.to_representation(pk)
        try:
            item = Competition.objects.get(pk=pk)
            serializer = CompetitionSerializer(item)
            return serializer.data
        except Competition.DoesNotExist:
            return None


class ChoiceField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        pk = super(ChoiceField, self).to_representation(value)
        if self.pk_field is not None:
            return self.pk_field.to_representation(pk)
        try:
            item = Choice.objects.get(pk=pk)
            if self.context.get("request"):
                serializer = ChoiceSerializer(
                    item,
                    context={
                        "include_is_correct": self.context.get("request").method
                        == "POST"
                    },
                )
            else:
                serializer = ChoiceSerializer(
                    item,
                    context={"include_is_correct": bool(self.context.get("create"))},
                )
            return serializer.data
        except Choice.DoesNotExist:
            return None


class UserCompetitionSerializer(serializers.ModelSerializer):
    registered_hints = HintSerializer(many=True, read_only=True)
    user_hints = serializers.PrimaryKeyRelatedField(
        many=True, queryset=HintAchivement.objects.all(), write_only=True
    )

    class Meta:
        model = UserCompetition
        fields = "__all__"
        read_only_fields = [
            "pk",
            "registered_hints",
            "user_hints",
            "user_profile",
            "is_winner",
            "amount_won",
            "tx_hash",
        ]

    def create(self, validated_data):
        competition = validated_data.get("competition")

        validated_data["hint_count"] = competition.hint_count

        return super().create(validated_data)


class UserCompetitionField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        pk = super(UserCompetitionField, self).to_representation(value)
        if self.pk_field is not None:
            return self.pk_field.to_representation(pk)
        try:
            item = UserCompetition.objects.get(pk=pk)
            serializer = UserCompetitionSerializer(item)
            return serializer.data
        except UserCompetition.DoesNotExist:
            return None


class UserAnswerSerializer(serializers.ModelSerializer):
    # user_competition = UserCompetitionField(
    #     queryset=UserCompetition.objects.filter(
    #         competition__is_active=True,
    #     )
    # )
    selected_choice = ChoiceField(queryset=Choice.objects.all())

    class Meta:
        model = UserAnswer
        fields = "__all__"


class CompetitionCreateSerializer(serializers.ModelSerializer):
    questions = QuestionCreateSerializer(many=True)
    user_profile = serializers.HiddenField(default=CurrentUserProfileDefault())
    is_active = serializers.HiddenField(default=False)

    class Meta:
        model = Competition
        fields = [
            "title",
            "details",
            "start_at",
            "is_active",
            "prize_amount",
            "chain_id",
            "token",
            "token_decimals",
            "token_address",
            "email_url",
            "telegram_url",
            "hint_count",
            "questions",
            "user_profile",
        ]

    def create(self, validated_data):
        questions_data = validated_data.pop("questions")
        competition = Competition.objects.create(**validated_data)
        for question_data in questions_data:
            choices_data = question_data.pop("choices")
            question = Question.objects.create(
                competition=competition, **question_data
            )  # Assuming a ForeignKey to Competition
            for choice_data in choices_data:
                Choice.objects.create(
                    question=question, **choice_data
                )  # Assuming a ForeignKey to Question
        return competition
