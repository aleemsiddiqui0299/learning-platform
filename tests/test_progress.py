import pytest
from rest_framework.test import APIClient
from base_project.models import Course


@pytest.mark.django_db
def test_local_progress_tracking_success():
    api_client = APIClient()
    course = Course.objects.create(title="Local Testing Course")

    payload = {"user_id": 101, "course_id": course.id, "second": 45}
    response = api_client.post('/api/v1/progress/', payload, format='json')

    assert response.status_code == 200
    assert response.data["status"] == "progress_saved"

@pytest.mark.django_db
def test_local_progress_tracking_invalid_course_returns_404():
    api_client = APIClient()
    course = Course.objects.create(title="Local Testing Course")

    payload = {"user_id": 101, "course_id": 777, "second": 45}
    response = api_client.post('/api/v1/progress/', payload, format='json')

    assert response.status_code == 404
