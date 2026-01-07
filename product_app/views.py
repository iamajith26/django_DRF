from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Catergory, ProductNew  # Import models here
from .serializers import ProductSerializer, CategorySerializer  # Create serializer below
from rest_framework.pagination import PageNumberPagination
from django.http import Http404, JsonResponse
import requests
from rest_framework.decorators import api_view, permission_classes
from .cache import ProductCacheManager
import logging

logger = logging.getLogger(__name__)

# Create your views here.
class ProductView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk=None):
        if pk:
            # Try to get from cache first
            cached_product = ProductCacheManager.get_product(pk)
            if cached_product:
                return Response(cached_product, status=status.HTTP_200_OK)
            
            # If not in cache, get from database
            try:
                product = ProductNew.objects.select_related('category').get(pk=pk)
                serializer = ProductSerializer(product)
                product_data = serializer.data
                
                # Cache the product data
                ProductCacheManager.set_product(pk, product_data)
                
                return Response(product_data, status=status.HTTP_200_OK)
            except ProductNew.DoesNotExist:
                raise Http404
        
        # Handle product list with caching
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # Generate filters for cache key
        filters = {
            'is_active': True,
            'order_by': 'name'
        }
        
        # Try to get from cache first
        cached_list = ProductCacheManager.get_product_list(page, page_size, filters)
        if cached_list:
            return Response(cached_list, status=status.HTTP_200_OK)
        
        # If not in cache, get from database
        paginator = PageNumberPagination()
        paginator.page_size = page_size
        products = ProductNew.objects.filter(is_active=True).select_related('category').order_by('name')
        results = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(results, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        
        # Cache the product list
        ProductCacheManager.set_product_list(response_data, page, page_size, filters)
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def post(self, request, pk=None, format=None):
        if 'activate_product' in request.path:  # Check if the request is for activation
            return self.activate(request, pk)
        
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            
            # Invalidate product list caches since we added a new product
            ProductCacheManager.invalidate_product_lists()
            
            custom_response = {
                "message": "Product created successfully",
            }    
            return Response(custom_response, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk, format=None):
        try:
            product = ProductNew.objects.get(id=pk)
        except ProductNew.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = ProductSerializer(instance=product, data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            
            # Invalidate cache for this specific product and product lists
            ProductCacheManager.invalidate_product(pk)
            ProductCacheManager.invalidate_product_lists()
            
            custom_response = {
                "message": "Product updated successfully",
            }
            return Response(custom_response, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        try:
            product = ProductNew.objects.get(id=pk)
            product.is_active = False  # Set is_active to False
            product.save()  # Save the changes
            
            # Invalidate cache for this specific product and product lists
            ProductCacheManager.invalidate_product(pk)
            ProductCacheManager.invalidate_product_lists()
            
            return Response({'message': 'Product successfully marked as inactive!'}, status=status.HTTP_200_OK)
        except ProductNew.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
        
    def activate(self, request, pk, format=None):
        try:
            product = ProductNew.objects.get(id=pk)
            product.is_active = True  # Set is_active to True
            product.save()  # Save the changes
            
            # Invalidate cache for this specific product and product lists
            ProductCacheManager.invalidate_product(pk)
            ProductCacheManager.invalidate_product_lists()
            
            return Response({'message': 'Product successfully reactivated!'}, status=status.HTTP_200_OK)
        except ProductNew.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
        
class CategoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk=None):
        if pk:
            try:
                category = Catergory.objects.get(pk=pk)
                serializer = CategorySerializer(category)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Catergory.DoesNotExist:
                raise Http404
        categories = Catergory.objects.filter(is_active=True).order_by('name') # Fetch only active categories
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, pk=None, format=None):
        if 'activate_category' in request.path:  # Check if the request is for activation
            return self.activate(request, pk)
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()  # Save the category to the database
            custom_response = {
                "message": "Category created successfully",
            }
            return Response(custom_response, status=status.HTTP_201_CREATED)  # Return the custom response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # Return validation errors
    
    def put(self, request, pk, format=None):
        category = Catergory.objects.get(id=pk)
        serializer = CategorySerializer(instance=category, data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            custom_response = {
                "message": "Category updated successfully",
            }
            return Response(custom_response, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        try:
            category = Catergory.objects.get(id=pk)  # Corrected to fetch category
            category.is_active = False  # Set is_active to False
            category.save()  # Save the changes
            return Response({'message': 'Category successfully marked as inactive!'}, status=status.HTTP_200_OK)
        except Catergory.DoesNotExist:
            return Response({'error': 'Category not found!'}, status=status.HTTP_404_NOT_FOUND)
        
    def activate(self, request, pk, format=None):
        try:
            category = Catergory.objects.get(id=pk)  # Corrected to fetch category
            category.is_active = True  # Set is_active to True
            category.save()  # Save the changes
            return Response({'message': 'Category successfully reactivated!'}, status=status.HTTP_200_OK)
        except Catergory.DoesNotExist:
            return Response({'error': 'Category not found!'}, status=status.HTTP_404_NOT_FOUND)
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_users(request):
    try:
        response = requests.get('https://jsonplaceholder.typicode.com/users')
        response.raise_for_status()  # Raise an error for bad responses
        users = response.json()
        return Response({'success': True, 'data': users}, status=status.HTTP_200_OK)
    except requests.RequestException as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
from rest_framework.parsers import MultiPartParser, FormParser
from .utils import S3Uploader

class FileUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, format=None):
        file = request.FILES.get('file')
        
        if not file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (2MB limit)
        if file.size > 2 * 1024 * 1024:
            return Response(
                {'error': 'File size exceeds 2MB limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Upload to S3
        uploader = S3Uploader()
        result = uploader.upload_file(file, folder='user-uploads')
        
        if result['success']:
            return Response({
                'message': 'File uploaded successfully',
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': result['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class FileDownloadView(APIView):
    def get(self, request):
        file_key = request.data.get('file_key')
        
        if not file_key:
            return Response(
                {'error': 'File key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploader = S3Uploader()
        file_content = uploader.generate_presigned_url(file_key)
        
        if file_content:
            return Response({'file_url': file_content}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Could not generate presigned URL'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FileDeleteView(APIView):
    def delete(self, request):
        uploader = S3Uploader()
        file_key = request.data.get('file_key')
        
        if not file_key:
            return Response(
                {'error': 'File key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = uploader.delete_file(file_key)
        
        if result['success']:
            return Response({'message': 'File deleted successfully'})
        else:
            return Response(
                {'error': result['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CacheManagementView(APIView):
    """View for cache management operations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get cache statistics"""
        stats = ProductCacheManager.get_cache_stats()
        return Response(stats, status=status.HTTP_200_OK)
    
    def delete(self, request):
        """Clear cache based on action parameter"""
        action = request.query_params.get('action', 'all')
        
        if action == 'products':
            ProductCacheManager.invalidate_all_products()
            message = "All product caches cleared"
        elif action == 'lists':
            ProductCacheManager.invalidate_product_lists()
            message = "Product list caches cleared"
        elif action == 'all':
            ProductCacheManager.invalidate_all_products()
            message = "All caches cleared"
        else:
            return Response(
                {'error': 'Invalid action. Use: products, lists, or all'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': message}, status=status.HTTP_200_OK)