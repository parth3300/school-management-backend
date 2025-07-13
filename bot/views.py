# Standard library imports
import json
import os
import logging
from datetime import datetime, timedelta
import threading
import logging
import time
import random

# Django imports
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

# Django REST Framework imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Google API imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bot.utils.google_oauth import create_google_meet_event
from school.models import Class, Student
from django.contrib.auth import get_user_model

User = get_user_model()

# Local imports
from .serializers import MeetingBotSerializer
from .tasks import MeetBot
# Initialize logger
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def meeting_bot_view(request):
    serializer = MeetingBotSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    email = getattr(settings, 'MEET_BOT_EMAIL', 'default@example.com')
    password = getattr(settings, 'MEET_BOT_PASSWORD', 'password')
    recording_dir = getattr(settings, 'RECORDING_DIR', 'recordings')

    # Ensure recording directory exists
    os.makedirs(recording_dir, exist_ok=True)

    # Correct way to format the string in Python (not using ${} like JavaScript)
    filename = f"reco{random.randint(1, 1000)}"  # or math.floor(random.random() * 1000) + 1
    print("New filename is .....", filename, data)
    filename = os.path.join(recording_dir,filename)
    logger.info(f"Starting meeting bot for meeting: {data['meeting_link']}")

    try:
        def run_bot():
            try:
                # First try with headless=False to debug
                bot = MeetBot(
                    email=email,
                    password=password,
                    meeting_link=data['meeting_link'],
                    filename=filename,
                    duration= data['duration'],
                    headless=False  # Start with visible browser for debugging
                )
                bot.run()
                
                # If successful, you can switch back to headless later
                # bot = MeetBot(..., headless=True)
                
            except Exception as e:
                logger.error(f"Error in bot thread: {str(e)}", exc_info=True)
                # Save additional debug info
                debug_info = {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "meeting_link": data['meeting_link'],
                    "email": email
                }
                with open(f"bot_error_{int(time.time())}.json", "w") as f:
                    json.dump(debug_info, f)

        thread = threading.Thread(target=run_bot)
        thread.daemon = True
        thread.start()
        thread.join()  # Waits for the thread to finish

        return Response(
            {
                "status": "success",
                "message": "Meeting bot started successfully",
                "meeting_link": data['meeting_link'],
                "recording_path": filename,
                "note": "Running in debug mode (visible browser)"
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Meeting bot failed to start: {str(e)}", exc_info=True)
        return Response(
            {
                "status": "error",
                "message": str(e),
                "solution": "Check if Google account requires additional verification or if the login page structure has changed"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



def get_attendees_for_meet(teacher_email, class_id):
    attendees = []
    attendees = [{"email": "parthdevops317@gmail.com"}]

    # ✅ Add the teacher
    if teacher_email:
        attendees.append({"email": teacher_email})

    # ✅ Add students from the class
    if class_id:
        try:
            selected_class = Class.objects.get(id=class_id)
            students = Student.objects.filter(current_class=selected_class)

            for student in students:
                if student.user.email:
                    attendees.append({"email": student.user.email})
        except Class.DoesNotExist:
            raise ValueError("Invalid class ID provided")

    return attendees


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_google_meet(request):
    try:
        title = request.data.get("title", "Auto Class")
        description = request.data.get("description", "Scheduled class")
        start_time = request.data.get("start_time")  # ISO format string
        end_time = request.data.get("end_time")      # ISO format string
        teacher_email = request.data.get("teacher_email")
        class_id = request.data.get("class_id")  # be sure to pass class_id, not `class`

        attendees = get_attendees_for_meet(teacher_email, class_id)


        meet_link = create_google_meet_event(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees
        )
        return Response({"meet_url": meet_link}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
