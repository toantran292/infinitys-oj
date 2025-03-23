from django.db import models

class Submission(models.Model):
    problem_id = models.CharField(max_length=100)
    submission_id = models.CharField(max_length=100, unique=True)
    code_content = models.TextField()
    language = models.CharField(max_length=50)
    time_limit = models.FloatField()
    memory_limit = models.IntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)