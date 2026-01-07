import pytest
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken
from unittest.mock import Mock, patch
from datetime import timedelta
import json

from .factories import UserFactory, AdminUserFactory, InactiveUserFactory
from .middleware import JWTMiddleware
from .views import ProtectedView


@pytest.mark.django_db
class TestUserFactory:
    """Test cases for User factories"""

    def test_user_factory_creates_valid_user(self):
        """Test that UserFactory creates a valid user with default settings"""
        user = UserFactory()
        
        assert user.username.startswith('testuser')
        assert user.email
        assert user.first_name
        assert user.last_name
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password('testpass123')  # Default password

    def test_user_factory_with_custom_password(self):
        """Test that UserFactory can create user with custom password"""
        custom_password = 'custompass456'
        user = UserFactory(password=custom_password)
        
        assert user.check_password(custom_password)
        assert not user.check_password('testpass123')

    def test_admin_user_factory(self):
        """Test that AdminUserFactory creates admin user"""
        admin = AdminUserFactory()
        
        assert admin.username.startswith('admin')
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True

    def test_inactive_user_factory(self):
        """Test that InactiveUserFactory creates inactive user"""
        user = InactiveUserFactory()
        
        assert user.username.startswith('inactive')
        assert user.is_active is False
        assert user.is_staff is False
        assert user.is_superuser is False


@pytest.mark.django_db
class TestJWTAuthentication:
    """Test cases for JWT token authentication endpoints"""

    def setup_method(self):
        """Set up test client and test user"""
        self.client = APIClient()
        self.user = UserFactory(
            username='testuser',
            password='testpass123'
        )
        self.admin = AdminUserFactory(
            username='adminuser',
            password='adminpass123'
        )
        self.inactive_user = InactiveUserFactory(
            username='inactiveuser',
            password='inactivepass123'
        )

    def test_token_obtain_pair_valid_credentials(self):
        """Test obtaining JWT tokens with valid credentials"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        
        # Verify tokens are valid
        access_token = response.data['access']
        refresh_token = response.data['refresh']
        assert access_token
        assert refresh_token

    def test_token_obtain_pair_invalid_credentials(self):
        """Test obtaining JWT tokens with invalid credentials"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'access' not in response.data
        assert 'refresh' not in response.data

    def test_token_obtain_pair_nonexistent_user(self):
        """Test obtaining JWT tokens with non-existent user"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'nonexistent',
            'password': 'anypassword'
        }
        
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_obtain_pair_inactive_user(self):
        """Test obtaining JWT tokens with inactive user"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'inactiveuser',
            'password': 'inactivepass123'
        }
        
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_obtain_pair_missing_fields(self):
        """Test obtaining JWT tokens with missing required fields"""
        url = reverse('token_obtain_pair')
        
        # Missing password
        response = self.client.post(url, {'username': 'testuser'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Missing username
        response = self.client.post(url, {'password': 'testpass123'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Missing both
        response = self.client.post(url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_refresh_valid_token(self):
        """Test refreshing JWT token with valid refresh token"""
        # First, get tokens
        login_url = reverse('token_obtain_pair')
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        login_response = self.client.post(login_url, login_data)
        refresh_token = login_response.data['refresh']
        
        # Now refresh the token
        refresh_url = reverse('token_refresh')
        refresh_data = {'refresh': refresh_token}
        
        response = self.client.post(refresh_url, refresh_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        
        # New access token should be different from original
        new_access_token = response.data['access']
        original_access_token = login_response.data['access']
        assert new_access_token != original_access_token

    def test_token_refresh_invalid_token(self):
        """Test refreshing JWT token with invalid refresh token"""
        refresh_url = reverse('token_refresh')
        refresh_data = {'refresh': 'invalid.token.here'}
        
        response = self.client.post(refresh_url, refresh_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_missing_token(self):
        """Test refreshing JWT token without providing refresh token"""
        refresh_url = reverse('token_refresh')
        
        response = self.client.post(refresh_url, {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_user_can_get_tokens(self):
        """Test that admin users can obtain JWT tokens"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'adminuser',
            'password': 'adminpass123'
        }
        
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data


@pytest.mark.django_db
class TestProtectedView:
    """Test cases for protected view that requires authentication"""

    def setup_method(self):
        """Set up test client and test user with tokens"""
        self.client = APIClient()
        self.user = UserFactory()
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

    def test_protected_view_with_valid_token(self):
        """Test accessing protected view with valid JWT token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        url = reverse('protected')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == "You are authenticated!"

    def test_protected_view_without_token(self):
        """Test accessing protected view without authentication token"""
        url = reverse('protected')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_view_with_invalid_token(self):
        """Test accessing protected view with invalid JWT token"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        
        url = reverse('protected')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_view_with_malformed_header(self):
        """Test accessing protected view with malformed authorization header"""
        # Missing 'Bearer' prefix
        self.client.credentials(HTTP_AUTHORIZATION=self.access_token)
        
        url = reverse('protected')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_view_with_expired_token(self):
        """Test accessing protected view with expired JWT token"""
        # Create an expired token using timedelta
        expired_token = AccessToken.for_user(self.user)
        expired_token.set_exp(lifetime=timedelta(seconds=-1))  # Set to expired
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(expired_token)}')
        
        url = reverse('protected')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_view_with_inactive_user_token(self):
        """Test accessing protected view with token for inactive user"""
        inactive_user = InactiveUserFactory()
        inactive_refresh = RefreshToken.for_user(inactive_user)
        inactive_access_token = str(inactive_refresh.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {inactive_access_token}')
        
        url = reverse('protected')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestJWTMiddleware:
    """Test cases for custom JWT middleware"""

    def setup_method(self):
        """Set up request factory and test users"""
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.inactive_user = InactiveUserFactory()
        
        # Create middleware instance
        self.get_response_mock = Mock(return_value=Mock())
        self.middleware = JWTMiddleware(self.get_response_mock)

    def _add_session_to_request(self, request):
        """Helper method to add session middleware to request"""
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

    def test_middleware_with_valid_jwt_token(self):
        """Test middleware correctly authenticates user with valid JWT"""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.headers = {'Authorization': f'Bearer {access_token}'}
        
        # Process request through middleware
        self.middleware(request)
        
        # Check that user was set correctly
        assert request.user == self.user
        assert request.user.is_authenticated

    def test_middleware_with_invalid_jwt_token(self):
        """Test middleware handles invalid JWT token gracefully"""
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.headers = {'Authorization': 'Bearer invalid.token.here'}
        
        # Process request through middleware
        self.middleware(request)
        
        # Check that anonymous user was set
        assert not request.user.is_authenticated

    def test_middleware_without_authorization_header(self):
        """Test middleware handles request without authorization header"""
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.headers = {}
        
        # Process request through middleware
        self.middleware(request)
        
        # Check that anonymous user was set
        assert not request.user.is_authenticated

    def test_middleware_with_malformed_authorization_header(self):
        """Test middleware handles malformed authorization header"""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.headers = {'Authorization': access_token}  # Missing 'Bearer'
        
        # Process request through middleware
        self.middleware(request)
        
        # Check that anonymous user was set
        assert not request.user.is_authenticated

    def test_middleware_with_inactive_user_token(self):
        """Test middleware handles token for inactive user"""
        refresh = RefreshToken.for_user(self.inactive_user)
        access_token = str(refresh.access_token)
        
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.headers = {'Authorization': f'Bearer {access_token}'}
        
        # Process request through middleware
        self.middleware(request)
        
        # Check that user is set but not authenticated due to inactive status
        assert not request.user.is_authenticated

    @patch('login_app.middleware.get_user')
    def test_middleware_with_already_authenticated_user(self, mock_get_user):
        """Test middleware doesn't override already authenticated user"""
        # Mock an already authenticated user from session
        mock_get_user.return_value = self.user
        
        refresh = RefreshToken.for_user(UserFactory())  # Different user
        access_token = str(refresh.access_token)
        
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.headers = {'Authorization': f'Bearer {access_token}'}
        
        # Process request through middleware
        self.middleware(request)
        
        # Should return the session user, not the JWT user
        assert request.user == self.user

    def test_middleware_get_jwt_user_with_expired_token(self):
        """Test middleware handles expired JWT token"""
        expired_token = AccessToken.for_user(self.user)
        expired_token.set_exp(lifetime=timedelta(seconds=-1))  # Set to expired
        
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.headers = {'Authorization': f'Bearer {str(expired_token)}'}
        
        # Process request through middleware
        self.middleware(request)
        
        # Check that anonymous user was set
        assert not request.user.is_authenticated


@pytest.mark.django_db
class TestJWTWorkflow:
    """Integration tests for complete JWT authentication workflow"""

    def setup_method(self):
        """Set up test client and test user"""
        self.client = APIClient()
        self.user = UserFactory(
            username='workflowuser',
            password='workflowpass123'
        )

    def test_complete_authentication_workflow(self):
        """Test complete workflow: login -> access protected resource -> refresh token"""
        # Step 1: Login and get tokens
        login_url = reverse('token_obtain_pair')
        login_data = {
            'username': 'workflowuser',
            'password': 'workflowpass123'
        }
        login_response = self.client.post(login_url, login_data)
        
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']
        
        # Step 2: Access protected resource with access token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        protected_url = reverse('protected')
        protected_response = self.client.get(protected_url)
        
        assert protected_response.status_code == status.HTTP_200_OK
        assert protected_response.data['message'] == "You are authenticated!"
        
        # Step 3: Refresh the access token
        refresh_url = reverse('token_refresh')
        refresh_data = {'refresh': refresh_token}
        refresh_response = self.client.post(refresh_url, refresh_data)
        
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.data['access']
        assert new_access_token != access_token
        
        # Step 4: Use new access token to access protected resource
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        final_response = self.client.get(protected_url)
        
        assert final_response.status_code == status.HTTP_200_OK
        assert final_response.data['message'] == "You are authenticated!"

    def test_workflow_with_logout_simulation(self):
        """Test workflow including token invalidation (logout simulation)"""
        # Login and get tokens
        login_url = reverse('token_obtain_pair')
        login_data = {
            'username': 'workflowuser',
            'password': 'workflowpass123'
        }
        login_response = self.client.post(login_url, login_data)
        access_token = login_response.data['access']
        
        # Access protected resource
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        protected_url = reverse('protected')
        response = self.client.get(protected_url)
        assert response.status_code == status.HTTP_200_OK
        
        # Simulate logout by clearing credentials
        self.client.credentials()  # Clear authorization header
        
        # Try to access protected resource without token
        response = self.client.get(protected_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db 
class TestEdgeCases:
    """Test edge cases and error scenarios"""

    def setup_method(self):
        """Set up test client"""
        self.client = APIClient()

    def test_token_endpoints_with_empty_payload(self):
        """Test token endpoints with empty JSON payload"""
        login_url = reverse('token_obtain_pair')
        response = self.client.post(login_url, {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_endpoints_with_null_values(self):
        """Test token endpoints with null values"""
        login_url = reverse('token_obtain_pair')
        # Use empty strings instead of None to avoid encoding issues
        data = {'username': '', 'password': ''}
        response = self.client.post(login_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_endpoints_with_extra_fields(self):
        """Test token endpoints ignore extra fields"""
        user = UserFactory(username='testuser', password='testpass123')
        login_url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'extra_field': 'should_be_ignored'
        }
        response = self.client.post(login_url, data)
        assert response.status_code == status.HTTP_200_OK

    def test_middleware_with_multiple_bearer_tokens(self):
        """Test middleware handles malformed header with multiple Bearer keywords"""
        factory = RequestFactory()
        middleware = JWTMiddleware(Mock())
        
        request = factory.get('/')
        # Add session to request
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        request.headers = {'Authorization': 'Bearer token1 Bearer token2'}
        
        middleware(request)
        
        # Should handle gracefully and not authenticate
        assert not request.user.is_authenticated
