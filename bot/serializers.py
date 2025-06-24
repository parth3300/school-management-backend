from rest_framework import serializers

class MeetingBotSerializer(serializers.Serializer):
    meeting_link = serializers.URLField(required=True)
    filename = serializers.CharField(required=True)
    duration_minutes = serializers.IntegerField(
        required=False,
        default=60
    )

