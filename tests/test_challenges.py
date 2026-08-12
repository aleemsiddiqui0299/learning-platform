import pytest
from rest_framework.test import APIClient
from base_project.celery import app as celery_app
from interactive_challenges.models import CodeChallenge, ChallengeResult
from interactive_challenges.tasks import validate_code_sandbox


@pytest.fixture(autouse=True)
def configure_celery_test_environment():
    """Forces Celery to process tasks synchronously inside the test database sandbox."""
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False

@pytest.mark.django_db
class TestInteractiveChallenges:
    def test_challenge_ingestion_saves_fields_correctly(self):
        client = APIClient()
        payload = {
            "course_id": 1,
            "title": "Asserting Truth",
            "instructions": "Ensure output returns true",
            "starter_code": "assert True",
            "expected_output": "PASS"
        }

        response = client.post('/api/v1/challenges/create/', payload, format='json')
        assert response.status_code == 201
        assert response.data["status"] == "challenge_created"

        # Verify row exists in PostgreSQL
        challenge = CodeChallenge.objects.get(id=response.data["challenge_id"])
        assert challenge.expected_output == "PASS"

    # def test_sandbox_task_logic_evaluates_correct_output(self):

    #     # mock lab inside the test database schema boundary
    #     challenge = CodeChallenge.objects.create(
    #         course_id=1,
    #         title="Unit Test Validation Lab",
    #         instructions="Output 'OK'",
    #         starter_code="print('OK')",
    #         expected_output="SUCCESS"   
    #     )

    #     # Act by running the celery task function synchronously to test tasks.py functions
    #     success_result = validate_code_sandbox(challenge.id, "SUCCESS")
    #     failure_result = validate_code_sandbox(challenge.id, "WRONG_OUTPUT_STRING")

    #     #Assert correct outcome dictionaries are generated for the frontend to consume
    #     assert success_result["passed"] is True
    #     assert "Correct" in success_result["message"]

    #     assert failure_result["passed"] is False
    #     assert "mismatch" in failure_result["message"]

    def test_submission_endpoint_triggers_synchronous_task_flow(self):
        # 1. Arrange a mock lab inside the test database schema boundary
        challenge = CodeChallenge.objects.create(
            course_id=1,
            title="API Inbound Submission Lab",
            instructions="Output 'OK'",
            starter_code="print('OK')",
            expected_output="SUCCESS"
        )
        
        client = APIClient()
        payload = {"output": "SUCCESS"}
        
        # 2. Act: Trigger our view over the simulated web request router layer
        response = client.post(f'/api/v1/challenges/{challenge.id}/submit/', payload, format='json')
        assert response.status_code == 202
        
        # 3. Assert: Verify the view instantly committed a result row to PostgreSQL
        uuid_token = response.data["tracking_task_id"]
        assert uuid_token is not None
        
        # Verify the eager celery task automatically updated its status to SUCCESS in DB
        db_record = ChallengeResult.objects.get(task_id=uuid_token)
        assert db_record.status == "SUCCESS"
        assert db_record.passed is True

    # def test_sandbox_task_logic_updates_database_record_correctly(self):
    #     challenge = CodeChallenge.objects.create(
    #         course_id=1,
    #         title="Unit Test Validation Lab",
    #         instructions="Output 'OK'",
    #         starter_code="print('OK')",
    #         expected_output="SUCCESS"
    #     )
        
    #     mock_task_uuid = "test-task-uuid-12345"
    #     ChallengeResult.objects.create(
    #         task_id=mock_task_uuid,
    #         challenge_id=challenge.id,
    #         status="PROCESSING"
    #     )
        
    #     # Execute the raw task logic synchronously
    #     validate_code_sandbox.apply(args=[challenge.id, "SUCCESS"], options={'task_id': mock_task_uuid})

    #     updated_record = ChallengeResult.objects.get(task_id=mock_task_uuid)
    #     assert updated_record.status == "SUCCESS"
    #     assert updated_record.passed is True
    #     assert "Correct" in updated_record.message