import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from prometheus_client import Summary, generate_latest, CONTENT_TYPE_LATEST
from django.http import HttpResponse
from .models import UserProgress, Course
from .tasks import trigger_completion_email

logger = logging.getLogger(__name__)

DB_WRITE_TIME = Summary('django_db_write_seconds', 'Time spent executing database progress updates')



class ProgressTrackingView(APIView):
    @DB_WRITE_TIME.time()
    def post(self, request):
        user_id = request.data.get("user_id")
        course_id = request.data.get("course_id")
        current_second = request.data.get("second", 0)

        logger.info(f"Processing progression state data transaction block for User: {user_id}, Course: {course_id}")

        if not user_id or not course_id:
            logger.warning("Aborting write pipeline due to missing required schema values.")
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        if not Course.objects.filter(id=course_id).exists():
            logger.warning(f"Aborting transaction: Target Course ID {course_id} missing from relational catalog.")
            return Response({
                "error":"Resource not found",
                "details":f"Course ID {course_id} does not exist in the learning catalog "
            },
            status = status.HTTP_404_NOT_FOUND)

        try:
            progress, created = UserProgress.objects.get_or_create(
                user_id=user_id, course_id=course_id
            )
            
            progress.last_watched_second = current_second

            if current_second >= 600 and not progress.is_completed:
                progress.is_completed=True
                trigger_completion_email.delay(user_id, course_id)

            progress.save()
            return Response({"status":"progress_saved", "is_completed": progress.is_completed})
        except Exception as e:
            logger.exception(" Catastrophic breakdown in progress tracking view:")
            return Response(
                {"error":"Internal Server Error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )       


def metrics_endpoint(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)