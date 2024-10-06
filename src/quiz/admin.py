from django.contrib import admin

from quiz.models import (
    Choice,
    Competition,
    Question,
    UserAnswer,
    UserCompetition,
    Sponsor,
    Hint,
    HintAchivement,
)


class CompetitionAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title",
        "details",
        "token",
    )

    search_fields = ("user_profile", "pk")
    list_filter = ()


class ChoiceInline(admin.TabularInline):
    model = Choice


class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "number",
        "competition",
    )

    inlines = (ChoiceInline,)

    list_filter = ("competition", "text")
    search_fields = ("competition", "number", "pk")


class ChoiceAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "question",
        "is_correct",
    )

    list_filter = ("question", "text")
    search_fields = ("question", "pk")


class UserAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "competition_title",
        "question_number",
    )
    search_fields = ("user_profile", "competition", "pk")

    @admin.display(ordering="question__number")
    def question_number(self, obj):
        return obj.question.number

    @admin.display(ordering="user_competition__competition__title")
    def competition_title(self, obj):
        return obj.user_competition.competition.title


class UserCompetitionAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "competition_title",
    )

    search_fields = ("user_profile", "competition", "pk")

    @admin.display(ordering="competition__title")
    def competition_title(self, obj):
        return obj.competition.title


admin.site.register(Competition, CompetitionAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)
admin.site.register(UserAnswer, UserAnswerAdmin)
admin.site.register(UserCompetition, UserCompetitionAdmin)
admin.site.register(Sponsor)

admin.site.register(Hint)
admin.site.register(HintAchivement)
