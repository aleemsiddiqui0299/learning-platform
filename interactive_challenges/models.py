from django.db import models

# Create your models here.
class CodeChallenge(models.Model):
    """Represents an interactive coding workspace snippet on the platform."""
    course_id = models.IntegerField()
    title = models.CharField(max_length=255)
    instructions = models.TextField()
    starter_code = models.TextField()
    expected_output = models.CharField(max_length=255)

    class Meta:
        indexes = [
            models.Index(fields = ['course_id'], name = 'idx_challenge_course_lookup'),
        ]

    def __str__(self):
        return self.title

class ChallengeResult(models.Model):
    """Stores asynchronous sandbox evaluation outcomes permanently inside the database."""
    task_id = models.CharField(max_length=255, unique=True) # The unique tracking token UUID
    challenge_id = models.IntegerField()
    status = models.CharField(max_length=50, default="PROCESSING") # PROCESSING, SUCCESS, FAILURE
    passed = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Task {self.task_id} - {self.status}"
