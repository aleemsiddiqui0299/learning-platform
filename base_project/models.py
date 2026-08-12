from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

class UserProgress(models.Model):
    user_id = models.IntegerField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    last_watched_second = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        #optimise rdbms lookups
        indexes = [
            # to accelerate get_or_create(user_id=x,course_id=y) with B-trees indexe
            models.Index(fields=['user_id', 'course'], name = 'idx_user_course_composite')
        ]

        unique_together = ('user_id', 'course')  