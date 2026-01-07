import pytest
from unittest.mock import patch, Mock
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .cache import ProductCacheManager
from .factories import CategoryFactory, ProductNewFactory, UserFactory
from .models import ProductNew


@pytest.mark.django_db
class TestProductCacheManager:
    """Test cases for ProductCacheManager"""

    def setup_method(self):
        """Set up test data"""
        self.cache_manager = ProductCacheManager
        cache.clear()  # Clear cache before each test

    def test_cache_key_generation(self):
        """Test cache key generation"""
        key = self.cache_manager._generate_cache_key("test", "123")
        assert key == "test:123"

    def test_list_cache_key_generation(self):
        """Test list cache key generation with different parameters"""
        key1 = self.cache_manager._generate_list_cache_key(1, 10, {'active': True})
        key2 = self.cache_manager._generate_list_cache_key(2, 10, {'active': True})
        key3 = self.cache_manager._generate_list_cache_key(1, 20, {'active': True})
        
        # All keys should be different
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_set_and_get_product(self):
        """Test setting and getting product from cache"""
        product_id = 123
        product_data = {'id': 123, 'name': 'Test Product'}
        
        # Set product in cache
        self.cache_manager.set_product(product_id, product_data)
        
        # Get product from cache
        cached_data = self.cache_manager.get_product(product_id)
        
        assert cached_data == product_data

    def test_get_nonexistent_product(self):
        """Test getting non-existent product from cache"""
        cached_data = self.cache_manager.get_product(999)
        assert cached_data is None

    def test_set_and_get_product_list(self):
        """Test setting and getting product list from cache"""
        list_data = {'results': [{'id': 1, 'name': 'Product 1'}], 'count': 1}
        
        # Set product list in cache
        self.cache_manager.set_product_list(list_data, page=1, page_size=10)
        
        # Get product list from cache
        cached_data = self.cache_manager.get_product_list(page=1, page_size=10)
        
        assert cached_data == list_data

    def test_invalidate_product(self):
        """Test invalidating specific product cache"""
        product_id = 123
        product_data = {'id': 123, 'name': 'Test Product'}
        
        # Set product in cache
        self.cache_manager.set_product(product_id, product_data)
        assert self.cache_manager.get_product(product_id) == product_data
        
        # Invalidate cache
        self.cache_manager.invalidate_product(product_id)
        
        # Should return None after invalidation
        assert self.cache_manager.get_product(product_id) is None

    @patch('product_app.cache.logger')
    def test_cache_error_handling(self, mock_logger):
        """Test cache error handling"""
        with patch('django.core.cache.cache.get', side_effect=Exception("Redis connection error")):
            result = self.cache_manager.get_product(123)
            assert result is None
            mock_logger.error.assert_called()


@pytest.mark.django_db
class TestProductViewCaching:
    """Test cases for ProductView caching functionality"""

    def setup_method(self):
        """Set up test client and test data"""
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        cache.clear()  # Clear cache before each test
        
        self.category = CategoryFactory(name="Electronics")
        self.product = ProductNewFactory(
            name="Test Laptop",
            category=self.category,
            is_active=True
        )

    def test_product_detail_caching(self):
        """Test that product detail is cached on first request"""
        url = reverse('get_product', kwargs={'pk': self.product.pk})
        
        # First request - should hit database and cache result
        with patch.object(ProductCacheManager, 'set_product') as mock_set:
            response = self.client.get(url)
            assert response.status_code == status.HTTP_200_OK
            mock_set.assert_called_once()
        
        # Second request - should hit cache
        with patch.object(ProductCacheManager, 'get_product', return_value=response.data):
            response2 = self.client.get(url)
            assert response2.status_code == status.HTTP_200_OK

    def test_product_list_caching(self):
        """Test that product list is cached"""
        url = reverse('product_list')
        
        # First request - should hit database and cache result
        with patch.object(ProductCacheManager, 'set_product_list') as mock_set:
            response = self.client.get(url)
            assert response.status_code == status.HTTP_200_OK
            mock_set.assert_called_once()

    def test_cache_invalidation_on_update(self):
        """Test that cache is invalidated when product is updated"""
        url = reverse('update_product', kwargs={'pk': self.product.pk})
        data = {'name': 'Updated Product', 'description': 'Updated', 'price': '99.99', 'stock': 10, 'category': self.category.id}
        
        # Cache invalidation should be called
        with patch.object(ProductCacheManager, 'invalidate_product') as mock_invalidate_product, \
             patch.object(ProductCacheManager, 'invalidate_product_lists') as mock_invalidate_lists:
            
            response = self.client.put(url, data)
            assert response.status_code == status.HTTP_200_OK
            mock_invalidate_product.assert_called_once_with(self.product.pk)
            mock_invalidate_lists.assert_called_once()

    def test_cache_invalidation_on_create(self):
        """Test that cache is invalidated when new product is created"""
        url = reverse('create_product')
        data = {
            'name': 'New Product',
            'description': 'New description',
            'price': '199.99',
            'stock': 5,
            'category': self.category.id
        }
        
        # Only list cache invalidation should be called for new products
        with patch.object(ProductCacheManager, 'invalidate_product_lists') as mock_invalidate_lists:
            response = self.client.post(url, data)
            assert response.status_code == status.HTTP_201_CREATED
            mock_invalidate_lists.assert_called_once()

    def test_cache_invalidation_on_delete(self):
        """Test that cache is invalidated when product is deleted"""
        url = reverse('delete_product', kwargs={'pk': self.product.pk})
        
        # Both individual and list cache invalidation should be called
        with patch.object(ProductCacheManager, 'invalidate_product') as mock_invalidate_product, \
             patch.object(ProductCacheManager, 'invalidate_product_lists') as mock_invalidate_lists:
            
            response = self.client.delete(url)
            assert response.status_code == status.HTTP_200_OK
            mock_invalidate_product.assert_called_once_with(self.product.pk)
            mock_invalidate_lists.assert_called_once()

    def test_pagination_cache_keys(self):
        """Test that different pagination parameters create different cache keys"""
        # Create multiple products
        ProductNewFactory.create_batch(15, category=self.category, is_active=True)
        
        # Request different pages
        url1 = reverse('product_list') + '?page=1&page_size=10'
        url2 = reverse('product_list') + '?page=2&page_size=10'
        url3 = reverse('product_list') + '?page=1&page_size=5'
        
        # Each should generate different cache keys
        with patch.object(ProductCacheManager, 'set_product_list') as mock_set:
            self.client.get(url1)
            self.client.get(url2)
            self.client.get(url3)
            
            assert mock_set.call_count == 3
            # Verify different cache parameters were used
            calls = mock_set.call_args_list
            assert calls[0][1]['page'] == 1 and calls[0][1]['page_size'] == 10
            assert calls[1][1]['page'] == 2 and calls[1][1]['page_size'] == 10
            assert calls[2][1]['page'] == 1 and calls[2][1]['page_size'] == 5


@pytest.mark.django_db
class TestCacheManagementView:
    """Test cases for CacheManagementView"""

    def setup_method(self):
        """Set up test client"""
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        cache.clear()

    def test_get_cache_stats(self):
        """Test getting cache statistics"""
        url = reverse('cache_management')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK

    def test_clear_all_caches(self):
        """Test clearing all caches"""
        url = reverse('cache_management') + '?action=all'
        
        with patch.object(ProductCacheManager, 'invalidate_all_products') as mock_invalidate:
            response = self.client.delete(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['message'] == 'All caches cleared'
            mock_invalidate.assert_called_once()

    def test_clear_product_caches_only(self):
        """Test clearing only product caches"""
        url = reverse('cache_management') + '?action=products'
        
        with patch.object(ProductCacheManager, 'invalidate_all_products') as mock_invalidate:
            response = self.client.delete(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['message'] == 'All product caches cleared'
            mock_invalidate.assert_called_once()

    def test_clear_list_caches_only(self):
        """Test clearing only list caches"""
        url = reverse('cache_management') + '?action=lists'
        
        with patch.object(ProductCacheManager, 'invalidate_product_lists') as mock_invalidate:
            response = self.client.delete(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['message'] == 'Product list caches cleared'
            mock_invalidate.assert_called_once()

    def test_invalid_cache_action(self):
        """Test invalid cache action parameter"""
        url = reverse('cache_management') + '?action=invalid'
        response = self.client.delete(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Invalid action' in response.data['error']

    def test_unauthorized_access_to_cache_management(self):
        """Test that unauthorized users cannot access cache management"""
        self.client.force_authenticate(user=None)
        url = reverse('cache_management')
        
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.django_db
class TestCacheIntegration:
    """Integration tests for caching functionality"""

    def setup_method(self):
        """Set up test client and test data"""
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        cache.clear()
        
        self.category = CategoryFactory()

    def test_end_to_end_cache_workflow(self):
        """Test complete cache workflow: create -> cache -> update -> invalidate"""
        # Step 1: Create product
        create_url = reverse('create_product')
        product_data = {
            'name': 'Cache Test Product',
            'description': 'Testing cache workflow',
            'price': '99.99',
            'stock': 10,
            'category': self.category.id
        }
        
        create_response = self.client.post(create_url, product_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        # Get the created product ID from database
        product = ProductNew.objects.get(name='Cache Test Product')
        
        # Step 2: Get product (should cache it)
        get_url = reverse('get_product', kwargs={'pk': product.pk})
        get_response = self.client.get(get_url)
        assert get_response.status_code == status.HTTP_200_OK
        
        # Verify product is now in cache
        cached_data = ProductCacheManager.get_product(product.pk)
        assert cached_data is not None
        assert cached_data['name'] == 'Cache Test Product'
        
        # Step 3: Update product (should invalidate cache)
        update_url = reverse('update_product', kwargs={'pk': product.pk})
        update_data = {
            'name': 'Updated Cache Product',
            'description': 'Updated description',
            'price': '149.99',
            'stock': 15,
            'category': self.category.id
        }
        
        update_response = self.client.put(update_url, update_data)
        assert update_response.status_code == status.HTTP_200_OK
        
        # Verify cache was invalidated
        cached_data_after_update = ProductCacheManager.get_product(product.pk)
        assert cached_data_after_update is None
        
        # Step 4: Get product again (should re-cache with updated data)
        get_response_2 = self.client.get(get_url)
        assert get_response_2.status_code == status.HTTP_200_OK
        
        # Verify updated data is cached
        cached_data_updated = ProductCacheManager.get_product(product.pk)
        assert cached_data_updated is not None
        assert cached_data_updated['name'] == 'Updated Cache Product'