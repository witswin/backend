from quiz.models import Competition


class CompetitionService:
    def __init__(self, competition_pk) -> None:
        self.competition = Competition.objects.get(pk=competition_pk)
