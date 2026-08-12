from celery import shared_task
import time
import logging
import os

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = "/app/course_completions_audit.txt"


@shared_task(name="base_project.tasks.trigger_completion_email")
def trigger_completion_email(user_id, course_id):
    logger.info(f"File Audit Pipeline: Intercepted completion notification for User: {user_id}")
    log_entry = (
        f"--- PLATFORM COMPLETION EVENT RECORD ---\n"
        f"Timestamp: {os.popen('date').read().strip()}\n"
        f"User ID: {user_id}\n"
        f"Course ID: {course_id}\n"
        f"Status: CERTIFICATE_GENERATED_AND_ISSUED\n"
        f"----------------------------------------\n"
    )

    try: 
        with open(AUDIT_LOG_PATH, "a") as audit_file:
            audit_file.write(log_entry)

        logger.info(f"File Audit Success: Record appended securely to {AUDIT_LOG_PATH}")
        return True
    except Exception as e:
        logger.error(f"File Audit Failure: Unable to write to workspace file system: {str(e)}")
        raise e