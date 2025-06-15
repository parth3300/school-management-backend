from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .serializers import MeetingBotSerializer
from .tasks import MeetBot
import threading
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def meeting_bot_view(request):
    serializer = MeetingBotSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    email = getattr(settings, 'MEET_BOT_EMAIL', 'default@example.com')
    password = getattr(settings, 'MEET_BOT_PASSWORD', 'password')

    logger.info(f"Starting meeting bot for meeting: {data['meeting_link']}")

    try:
        def run_bot():
            try:
                bot = MeetBot(
                    email=email,
                    password=password,
                    meeting_link=data['meeting_link'],
                    filename=data['filename']
                )
                bot.run()
            except Exception as e:
                logger.error(f"Error in bot thread: {str(e)}")

        thread = threading.Thread(target=run_bot)
        thread.daemon = True
        thread.start()

        return Response(
            {
                "status": "success",
                "message": "Meeting bot started successfully",
                "meeting_link": data['meeting_link']
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Meeting bot failed to start: {str(e)}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
