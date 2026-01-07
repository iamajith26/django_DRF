import pytest
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Example Model for demonstration
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

@pytest.mark.django_db
class TestBlogPostModel:
    """Test cases for BlogPost model"""
    
    def test_model_creation(self, user_factory):
        """Test model can be created with valid data"""
        user = user_factory()
        post = BlogPost.objects.create(
            title="Test Post",
            content="Test content",
            author=user
        )
        assert post.title == "Test Post"
        assert post.author == user
        assert str(post) == "Test Post"
    
    def test_model_fields(self, user_factory):
        """Test model fields and constraints"""
        user = user_factory()
        post = BlogPost.objects.create(
            title="Test Post",
            content="Test content", 
            author=user,
            is_published=True
        )
        assert post.is_published is True
        assert post.created_at is not None
    
    def test_model_relationships(self, user_factory):
        """Test model relationships"""
        user = user_factory()
        post1 = BlogPost.objects.create(title="Post 1", content="Content", author=user)
        post2 = BlogPost.objects.create(title="Post 2", content="Content", author=user)
        
        user_posts = user.blogpost_set.all()
        assert post1 in user_posts
        assert post2 in user_posts
        assert user_posts.count() == 2