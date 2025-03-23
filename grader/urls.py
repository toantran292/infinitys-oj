from django.urls import path
from .views import SubmitCodeView

urlpatterns = [
    path("submit", SubmitCodeView.as_view(), name="submit_code"),
]
