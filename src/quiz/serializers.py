import random
from typing import Any

from django.utils import timezone
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
    CompetitionHint,
    UserCompetitionHint,
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


class CompetitionHintSerializer(serializers.ModelSerializer):
    hint = HintSerializer()

    class Meta:
        model = CompetitionHint
        exclude = ("created_at", "competition")


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
    built_in_hints = CompetitionHintSerializer(
        many=True, read_only=True, source="competitionhint_set"
    )

    allowed_hint_types = HintSerializer(many=True, read_only=True)

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
    # registered_hints = HintSerializer(many=True, read_only=True)
    registered_hints = serializers.SerializerMethodField()

    user_hints = serializers.PrimaryKeyRelatedField(
        many=True, queryset=HintAchivement.objects.all(), write_only=True
    )

    class Meta:
        model = UserCompetition
        fields = "__all__"
        read_only_fields = [
            "pk",
            "registered_hints",
            "user_profile",
            "is_winner",
            "amount_won",
            "tx_hash",
        ]

    def get_registered_hints(self, obj: UserCompetition):
        return HintSerializer(
            Hint.objects.filter(
                usercompetitionhint__user_competition=obj,
                usercompetitionhint__is_used=False,
            ),
            many=True,
        ).data

    def create(self, validated_data):
        competition = validated_data.get("competition")

        builtin_hints = competition.competitionhint_set.all()
        allowed_user_hints = competition.allowed_hint_types.all()

        user_hints = HintAchivement.objects.filter(
            user_profile=validated_data.get("user_profile"),
            is_used=False,
            hint__in=allowed_user_hints,
            pk__in=map(lambda x: x.pk, validated_data.pop("user_hints")),
        )

        instance = super().create(validated_data)

        max_hint_count = competition.hint_count

        combined_hints = list(builtin_hints) + list(user_hints)

        registered_hints = 0

        for hint in combined_hints:
            if max_hint_count <= registered_hints:
                break

            if isinstance(hint, HintAchivement):
                hint.is_used = True
                hint.used_at = timezone.now()
                hint.save()
                UserCompetitionHint.objects.create(
                    user_competition=instance,
                    hint=hint.hint,
                    is_used=False,
                    question=None,
                )
                instance.registered_hints.add(hint.hint)
                registered_hints += 1
            else:
                registered_hints += hint.count
                for _ in range(min(hint.count, max_hint_count - registered_hints)):
                    UserCompetitionHint.objects.create(
                        user_competition=instance,
                        hint=hint.hint,
                        is_used=False,
                        question=None,
                    )

                    instance.registered_hints.add(hint.hint)

        return instance


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


class CompetitionHintCreateSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    hint = serializers.PrimaryKeyRelatedField(
        queryset=Hint.objects.all(), write_only=True
    )


class CompetitionCreateSerializer(serializers.ModelSerializer):
    questions = QuestionCreateSerializer(many=True)
    user_profile = serializers.HiddenField(default=CurrentUserProfileDefault())
    is_active = serializers.HiddenField(default=False)
    builtin_hints = CompetitionHintCreateSerializer(write_only=True, many=True)
    allowed_hint_types = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Hint.objects.all(), write_only=True
    )

    class Meta:
        model = Competition
        fields = [
            "id",
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
            "builtin_hints",
            "allowed_hint_types"
        ]

    def create(self, validated_data):
        questions_data = validated_data.pop("questions")
        allowed_hints = validated_data.pop("allowed_hint_types")
        builtin_hints = validated_data.pop("builtin_hints")

        competition = Competition.objects.create(**validated_data)


        for hint in builtin_hints:
            CompetitionHint.objects.create(
                competition=competition, **hint
            )

        for hint in allowed_hints:
            competition.allowed_hint_types.add(
                hint
            )

        competition.save()

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
