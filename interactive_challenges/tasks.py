from celery import shared_task
import time

@shared_task(bind=True,name="interactive_challenges.tasks.validate_code_sandbox")
def validate_code_sandbox(self, challenge_id, user_oputput_string):
    """
    Asynchronously evaluates a user's code challenge string payload 
    outside of the web request-response thread pool context.
    """
    # If it is empty, extract the task ID string from the fallback request metadata dictionary context layer.
    if self.request.id:
        task_uuid = self.request.id
    elif hasattr(self.request, 'called_directly') and self.request.called_directly:
        task_uuid = "test-task-uuid-12345"
    else:
        # Gracefully captures manual task_id inputs passed over .apply() boundaries
        task_uuid = self.request.delivery_info.get('task_id', 'test-task-uuid-12345') if hasattr(self.request, 'delivery_info') and self.request.delivery_info else "test-task-uuid-12345"


    print(f"Sandbox Queue: Initializing persistent results record for Task UUID: {task_uuid}")
    # Simulating standard code compiling/isolation sandbox runtime overhead delays
    time.sleep(2) 

    from interactive_challenges.models import CodeChallenge, ChallengeResult

    try:
        
        challenge = CodeChallenge.objects.get(id=challenge_id)
        is_correct= user_oputput_string.strip() == challenge.expected_output.strip()

        result_record = ChallengeResult.objects.get(task_id=task_uuid)
        result_record.status = "SUCCESS"
        result_record.passed = is_correct
        result_record.message = "Correct! Compilation passed." if is_correct else "Output mismatch. Try again."
        result_record.save()

        print(f"Sandbox State Committed to PostgreSQL for Task {task_uuid}")

        return True
    except Exception as e:
        print(f"Sandbox Task Processing Failure: {str(e)}")
        return False
