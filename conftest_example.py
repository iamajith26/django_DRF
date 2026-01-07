import os
import django
import pytest
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth.models import User

def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
    django.setup()

@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def create_user(**kwargs):
        defaults = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        return user
    return create_user

@pytest.fixture
def api_client():
    """API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def request_factory():
    """Request factory for testing."""
    return RequestFactory()