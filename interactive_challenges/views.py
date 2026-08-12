import logging
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CodeChallenge, ChallengeResult
from .tasks import validate_code_sandbox
from celery.result import AsyncResult
from prometheus_client import Summary, Counter
from django.db import transaction
import uuid

logger = logging.getLogger(__name__)    

# OBSERVABILITY METRICS PLATFORM DEFINITION

CHALLENGE_CREATION_TIME = Summary('challenge_ingestion_seconds', 'Time spent processing and saving new interactive coding labs')

SANDBOX_SUBMISSIONS_TOTAL = Counter('sandbox_submissions_total', 'Total number of user code strings dispatched to the Celery sandbox')

# Create your views here.
class ChallengeIngestionView(APIView):

    @CHALLENGE_CREATION_TIME.time() # metric for execution duration
    def post(self, request):
        # API Endpoint to create a new interactive coding lab on the platform

        course_id = request.data.get("course_id")
        title = request.data.get("title")

        logger.info(f"Ingesting new interactive code lab structure for Course ID: {course_id}")

        instructions = request.data.get("instructions")
        starter_code = request.data.get("starter_code")
        expected_output = request.data.get("expected_output")

        if not all([course_id, title, instructions, starter_code, expected_output]):
            logger.warning("Aborting challenge injection due to missing structural parameters.")
            return Response({"error": "Missing required properties"}, status=status.HTTP_400_BAD_REQUEST)

        challenge = CodeChallenge.objects.create(
            course_id=course_id, title=title, instructions=instructions,
            starter_code=starter_code, expected_output=expected_output
        )
        logger.info(f"Challenge created successfully. Primary Key locked: {challenge.id}")
        return Response({"status": "challenge_created", "challenge_id": challenge.id}, status=status.HTTP_201_CREATED)

class ChallengeSubmissionView(APIView):
    """Validates user code execution submissions."""
    def post(self, request, pk):
        logger.info(f"Intercepting user solution submission for Challenge ID: {pk}")

        if not CodeChallenge.objects.filter(pk=pk).exists():
            logger.warning(f"Challenge Lookup Failed: ID {pk} does not exist.")
            return Response({"error": "Challenge not found"}, status=status.HTTP_404_NOT_FOUND)


        # Incrementing telemetry counter metric upon valid interception
        SANDBOX_SUBMISSIONS_TOTAL.inc()

        user_submitted_output = request.data.get("output", "").strip()
        task_uuid = str(uuid.uuid4())
        

        # Immediately insert an initial tracking row set to PROCESSING
        ChallengeResult.objects.get_or_create(
            task_id=task_uuid,
            defaults={
                'challenge_id': pk,
                'status': 'PROCESSING'
            }
        )

        # Fire the task to Celery
        validate_code_sandbox.apply_async(
            args=[pk, user_submitted_output], 
            task_id=task_uuid 
        )

        logger.info(f"Code execution safely deferred to Sandbox Queue. Async Tracking Token: {task_uuid}")
        return Response({
            "status": "EVALUATION_QUEUED_IN_SANDBOX",
            "tracking_task_id": task_uuid,
            "details": "Your code compilation execution loop is running asynchronously in our cluster."
        },
        status = status.HTTP_202_ACCEPTED)

class ChallengeTaskStatusView(APIView):
    # API Endpoint to fetch the asynchronous execution result of a sandbox compilation.
    def get(self, request, task_id):
        logger.info(f"Task Status View called for taskId -> {task_id}")
        # Inspect the Celery result backend via the task UUID token
        with transaction.atomic():
            try:
                # Look up the row in your new persistent results table
                record = ChallengeResult.objects.get(task_id=task_id)
                logger.info(f"Status for task ID {task_id} is {record.status}")
                return Response({
                    "task_id": record.task_id,
                    "status": record.status, # PROCESSING or SUCCESS
                    "result": {
                        "challenge_id": record.challenge_id,
                        "passed": record.passed,
                        "message": record.message
                    }
                }, status=status.HTTP_200_OK)
            except ChallengeResult.DoesNotExist:
                # If the record hasn't hit DB yet, safely fall back to a processing state dictionary
                return Response({
                    "task_id": task_id,
                    "status": "PROCESSING",
                    "result": None
                }, status=status.HTTP_200_OK)