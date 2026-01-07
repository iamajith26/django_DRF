import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

@pytest.mark.django_db
class TestBlogViews:
    """Test cases for Blog views"""
    
    def test_list_view_get(self, api_client, user_factory):
        """Test GET request to list view"""
        user = user_factory()
        api_client.force_authenticate(user=user)
        
        url = reverse('blog-list')  # Adjust URL name as needed
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)
    
    def test_create_view_post_valid_data(self, api_client, user_factory):
        """Test POST request with valid data"""
        user = user_factory()
        api_client.force_authenticate(user=user)
        
        data = {
            'title': 'New Post',
            'content': 'Post content',
            'is_published': True
        }
        url = reverse('blog-list')
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Post'
    
    def test_create_view_post_invalid_data(self, api_client, user_factory):
        """Test POST request with invalid data"""
        user = user_factory()
        api_client.force_authenticate(user=user)
        
        data = {'title': ''}  # Missing required fields
        url = reverse('blog-list')
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_detail_view_get(self, api_client, user_factory):
        """Test GET request to detail view"""
        user = user_factory()
        api_client.force_authenticate(user=user)
        
        # Create test object first
        from .models import BlogPost
        post = BlogPost.objects.create(
            title="Test Post",
            content="Content",
            author=user
        )
        
        url = reverse('blog-detail', kwargs={'pk': post.pk})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == post.pk
    
    def test_unauthorized_access(self, api_client):
        """Test unauthorized access is denied"""
        url = reverse('blog-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED