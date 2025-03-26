from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
import json
from .models import Submission
from .tasks import grade_submission

@method_decorator(csrf_exempt, name='dispatch')
class SubmitCodeView(View):
    def post(self, request):
        print("hi")
        try:
            data = json.loads(request.body)
            required_fields = [
                "problem_id", "submission_id", "code_content",
                "language", "time_limit", "memory_limit"
            ]
            if not all(field in data for field in required_fields):
                return JsonResponse({"error": "Missing required fields."}, status=400)

            submission = Submission.objects.create(
                problem_id=data["problem_id"],
                submission_id=data["submission_id"],
                code_content=data["code_content"],
                language=data["language"],
                time_limit=data["time_limit"],
                memory_limit=data["memory_limit"]
            )

            grade_submission.delay(submission.id)
            return JsonResponse({"status": "submitted"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)