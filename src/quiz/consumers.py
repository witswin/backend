import json
from typing import Any, Type
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
)
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Q, Count
from authentication.models import UserProfile
from quiz.serializers import (
    CompetitionSerializer,
    QuestionSerializer,
    UserAnswerSerializer,
    UserCompetitionSerializer,
)
from quiz.utils import (
    get_previous_round_losses,
    get_quiz_question_state,
    get_round_participants,
    is_user_eligible_to_participate,
)
from quiz.services.competition_service import CompetitionService
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from djangorestframework_camel_case.util import underscoreize
from .models import Competition, Question, Choice, UserCompetition, UserAnswer
from django.core.cache import cache

import json
import logging


logger = logging.getLogger(__name__)


class BaseJsonConsumer(AsyncJsonWebsocketConsumer):

    async def disconnect(self, close_code):
        await self.close()
        if not self.channel_layer:
            return

        await self.channel_layer.group_discard(
            self.competition_group_name, self.channel_name
        )

    async def send_json(self, content, close=False):
        """
        Encode the given content as JSON and send it to the client.
        """
        await super().send(text_data=await self.encode_json(content), close=close)

    @classmethod
    async def encode_json(cls, content):
        return CamelCaseJSONRenderer().render(content).decode("utf-8")

    @database_sync_to_async
    def resolve_user(self):
        if hasattr(self.scope["user"], "profile"):
            return self.scope["user"].profile

        return None


class QuizListConsumer(BaseJsonConsumer):
    @database_sync_to_async
    def get_quiz_list(self):
        return CompetitionSerializer(
            Competition.objects.filter(is_active=True).order_by("-created_at"),
            many=True,
        ).data

    @database_sync_to_async
    def get_enrollments_list(self):
        if not self.user_profile:
            return []

        return UserCompetitionSerializer(
            UserCompetition.objects.filter(user_profile=self.user_profile),
            many=True,
        ).data

    async def connect(self):
        self.competition_group_name = "quiz_list"
        self.user_profile = await self.resolve_user()

        await self.accept()

        if not self.channel_layer:
            return

        await self.channel_layer.group_add(
            self.competition_group_name, self.channel_name
        )

        await self.send_json(
            {"type": "competition_list", "data": await self.get_quiz_list()}
        )
        await self.send_json(
            {"type": "user_enrolls", "data": await self.get_enrollments_list()}
        )

    @database_sync_to_async
    def resolve_competition(self, pk):
        competition = Competition.objects.get(pk=pk)

        return CompetitionSerializer(instance=competition).data

    async def update_competition_data(self, event):
        pk = event["data"]

        data = await self.resolve_competition(pk)

        if data["is_active"] is False:
            await self.delete_competition(event)
            return

        await self.send_json({"type": "update_competition", "data": data})

    async def increase_enrollment(self, event):
        await self.send_json({"type": "increase_enrollment", "data": event["data"]})

    async def delete_competition(self, event):
        pk = event["data"]

        await self.send_json({"type": "remove_competition", "data": pk})


class QuizConsumer(BaseJsonConsumer):
    user_competition: UserCompetition
    user_profile: UserProfile

    service: CompetitionService

    @database_sync_to_async
    def send_user_answers(self):
        if not self.user_profile:
            return []

        return self.service.send_user_answers(self.user_profile, self.user_competition)

    @database_sync_to_async
    def resolve_user_competition(self):
        return self.service.get_user_competition(self.user_profile)

    @database_sync_to_async
    def send_hint_question(self, question_id):
        if not self.user_competition:
            return

        return self.service.resolve_hint(self.user_competition, question_id)

    async def send_question(self, event):
        question_data = event["data"]

        await self.send_json(
            {
                "question": {
                    **json.loads(question_data),
                    "is_eligible": await self.is_user_eligible_to_participate(),
                },
                "type": "new_question",
            }
        )

    async def send_quiz_stats(self, event):
        state = event["data"]
        await self.send_json(await self.get_quiz_stats(state))

    @database_sync_to_async
    def calculate_quiz_winners(self):
        return self.service.calculate_quiz_winners(self.user_competition)

    async def finish_quiz(self, event):
        winners = await self.calculate_quiz_winners()
        await self.send_json({"winners_list": winners, "type": "quiz_finish"})

    @database_sync_to_async
    def get_question(self, index: int):
        return self.service.get_question(
            self.user_competition, index, self.user_profile
        )

    @database_sync_to_async
    def is_user_eligible_to_participate(self):
        return is_user_eligible_to_participate(
            user_profile=self.user_profile, competition=self.competition
        )

    @database_sync_to_async
    def get_quiz_stats(self, state=None):
        return self.service.get_quiz_stats(self.user_competition, state)

    @database_sync_to_async
    def get_current_question(self):
        return self.service.get_current_question(self.user_competition)

    @database_sync_to_async
    def get_competition_stats(self) -> Any:
        return CompetitionSerializer(instance=self.competition).data

    @database_sync_to_async
    def resolve_service(self, competition_pk: int):
        return CompetitionService(competition_pk)

    async def connect(self):
        self.competition_id = self.scope["url_route"]["kwargs"]["competition_id"]
        self.service = await self.resolve_service(self.competition_id)
        self.competition_group_name = f"quiz_{self.competition_id}"
        self.competition: Competition = self.service.competition
        self.user_profile = await self.resolve_user()
        self.user_competition = await self.resolve_user_competition()

        await self.accept()

        if not self.channel_layer:
            return

        await self.channel_layer.group_add(
            self.competition_group_name, self.channel_name
        )

        await self.send_json(
            {"type": "answers_history", "data": await self.send_user_answers()}
        )

        await self.send_json(await self.get_quiz_stats())

        if self.competition.start_at > timezone.now():
            await self.send_json({"type": "idle", "message": "wait for quiz to start"})

        elif await database_sync_to_async(lambda: self.competition.is_in_progress)():
            await self.send_json(await self.get_current_question())
        else:
            await self.finish_quiz(None)

    async def send_correct_answer(self, event):
        data = event["data"]

        await self.send_json({"type": "correct_answer", "data": data})

    async def handle_user_command(self, command, args):
        if command == "GET_CURRENT_QUESTION":
            return await self.send_json(await self.get_current_question())

        if command == "GET_COMPETITION":
            return await self.send_json(await self.get_competition_stats())

        if command == "GET_STATS":
            return await self.send_json(await self.get_quiz_stats())

        if command == "GET_HINT":
            hint_choices = await self.send_hint_question(args["question_id"])

            await self.send_json(
                {
                    "type": "hint_question",
                    "data": hint_choices,
                    "question_id": args["question_id"],
                }
            )

        if command == "ANSWER":
            is_eligible = await self.is_user_eligible_to_participate()
            if is_eligible is False:
                return

            res = await self.save_answer(
                args["question_id"],
                args["selected_choice_id"],
            )

            await self.send_json(
                {
                    "type": "add_answer",
                    "data": {
                        **res,
                        "is_eligible": res["is_correct"],
                        "question_id": args["question_id"],
                    },
                }
            )

    async def receive(self, text_data):
        data = underscoreize(json.loads(text_data))
        command = data["command"]

        if command == "PING":
            await self.send("PONG")

        try:
            await self.handle_user_command(command, data.get("args", {}))
        except Exception as e:
            logger.warning(f"Error while handling user command: {e}")

    @database_sync_to_async
    def save_answer(self, question_id, selected_choice_id):
        if not self.user_competition:
            return {"error": "user has not joined this competition"}

        return self.service.save_user_answer(
            self.user_competition, question_id, selected_choice_id
        )
