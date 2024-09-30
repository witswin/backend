from rest_framework import views
from rest_framework.response import Response
from django.core.cache import cache
from authentication.models import UserProfile
from quiz.models import Competition, UserCompetition
from .models import AppSettting


class GeneralStatsView(views.APIView):
    def get(self, request) -> Response:
        analytics = cache.get("analytics_users_count")
        if analytics is None:
            all_users_count = UserProfile.objects.count()
            competitions_count = Competition.objects.count()
            user_enrollments_count = UserCompetition.objects.all().count()
            analytics = {
                "all_users_count": all_users_count,
                "competitions_count": competitions_count,
                "user_enrollments_count": user_enrollments_count,
                "total_prize_amount": AppSettting.objects.get_key(
                    "total_prize_amount"
                ).value,
            }
            cache.set("analytics_users_count", analytics, timeout=2 * 60)

        return Response(analytics)
