import os
import django
from django.conf import settings

def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_DRF.settings')
    django.setup()