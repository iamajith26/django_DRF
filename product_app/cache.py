import hashlib
import json
from django.core.cache import cache
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
import logging

logger = logging.getLogger(__name__)

class ProductCacheManager:
    """Manages caching for product data"""
    
    CACHE_PREFIX = "product"
    CACHE_LIST_PREFIX = "product_list"
    DEFAULT_TTL = getattr(settings, 'CACHE_TTL', 900)  # 15 minutes
    
    @classmethod
    def _generate_cache_key(cls, prefix, identifier):
        """Generate cache key with prefix and identifier"""
        return f"{prefix}:{identifier}"
    
    @classmethod
    def _generate_list_cache_key(cls, page=1, page_size=10, filters=None):
        """Generate cache key for product list with pagination and filters"""
        key_data = {
            'page': page,
            'page_size': page_size,
            'filters': filters or {}
        }
        key_string = json.dumps(key_data, sort_keys=True, cls=DjangoJSONEncoder)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return cls._generate_cache_key(cls.CACHE_LIST_PREFIX, key_hash)
    
    @classmethod
    def get_product(cls, product_id):
        """Get cached product by ID"""
        cache_key = cls._generate_cache_key(cls.CACHE_PREFIX, product_id)
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT for product {product_id}")
                return cached_data
            logger.info(f"Cache MISS for product {product_id}")
            return None
        except Exception as e:
            logger.error(f"Cache error while getting product {product_id}: {e}")
            return None
    
    @classmethod
    def set_product(cls, product_id, product_data, ttl=None):
        """Cache product data"""
        cache_key = cls._generate_cache_key(cls.CACHE_PREFIX, product_id)
        ttl = ttl or cls.DEFAULT_TTL
        try:
            cache.set(cache_key, product_data, ttl)
            logger.info(f"Cached product {product_id} for {ttl} seconds")
        except Exception as e:
            logger.error(f"Cache error while setting product {product_id}: {e}")
    
    @classmethod
    def get_product_list(cls, page=1, page_size=10, filters=None):
        """Get cached product list"""
        cache_key = cls._generate_list_cache_key(page, page_size, filters)
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT for product list (page {page})")
                return cached_data
            logger.info(f"Cache MISS for product list (page {page})")
            return None
        except Exception as e:
            logger.error(f"Cache error while getting product list: {e}")
            return None
    
    @classmethod
    def set_product_list(cls, product_list_data, page=1, page_size=10, filters=None, ttl=None):
        """Cache product list data"""
        cache_key = cls._generate_list_cache_key(page, page_size, filters)
        ttl = ttl or cls.DEFAULT_TTL
        try:
            cache.set(cache_key, product_list_data, ttl)
            logger.info(f"Cached product list (page {page}) for {ttl} seconds")
        except Exception as e:
            logger.error(f"Cache error while setting product list: {e}")
    
    @classmethod
    def invalidate_product(cls, product_id):
        """Invalidate cached product"""
        cache_key = cls._generate_cache_key(cls.CACHE_PREFIX, product_id)
        try:
            cache.delete(cache_key)
            logger.info(f"Invalidated cache for product {product_id}")
        except Exception as e:
            logger.error(f"Error invalidating cache for product {product_id}: {e}")
    
    @classmethod
    def invalidate_product_lists(cls):
        """Invalidate all cached product lists"""
        try:
            # Get all cache keys that match the list prefix pattern
            cache_pattern = f"{cls.CACHE_LIST_PREFIX}:*"
            cache.delete_many(cache.keys(cache_pattern))
            logger.info("Invalidated all product list caches")
        except Exception as e:
            logger.error(f"Error invalidating product list caches: {e}")
    
    @classmethod
    def invalidate_all_products(cls):
        """Invalidate all product caches"""
        try:
            # Invalidate individual products
            product_pattern = f"{cls.CACHE_PREFIX}:*"
            cache.delete_many(cache.keys(product_pattern))
            
            # Invalidate product lists
            cls.invalidate_product_lists()
            logger.info("Invalidated all product caches")
        except Exception as e:
            logger.error(f"Error invalidating all product caches: {e}")
    
    @classmethod
    def get_cache_stats(cls):
        """Get cache statistics (if Redis backend supports it)"""
        try:
            cache_backend = cache._cache
            if hasattr(cache_backend, 'get_stats'):
                return cache_backend.get_stats()
            return {"message": "Cache stats not available for this backend"}
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}