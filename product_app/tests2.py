import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from decimal import Decimal
import io

from .models import Catergory, ProductNew
from .factories import CategoryFactory, ProductNewFactory, UserFactory
from .serializers import CategorySerializer, ProductSerializer


# Category Model Tests
@pytest.mark.django_db
def test_category_creation():
    """Test category can be created with valid data"""
    category = CategoryFactory()
    assert category.name
    assert category.description
    assert category.is_active is True
    assert str(category) == category.name


@pytest.mark.django_db
def test_category_unique_name():
    """Test category name must be unique"""
    CategoryFactory(name="Unique Category")
    with pytest.raises(Exception):  # IntegrityError for unique constraint
        CategoryFactory(name="Unique Category")


@pytest.mark.django_db
def test_category_ordering():
    """Test categories are ordered by name"""
    cat_z = CategoryFactory(name="Z Category")
    cat_a = CategoryFactory(name="A Category")
    cat_m = CategoryFactory(name="M Category")
    
    categories = Catergory.objects.all()
    assert categories[0].name == "A Category"
    assert categories[1].name == "M Category"
    assert categories[2].name == "Z Category"


# Product Model Tests
@pytest.mark.django_db
def test_product_creation():
    """Test product can be created with valid data"""
    product = ProductNewFactory()
    assert product.name
    assert product.description
    assert product.price > 0
    assert product.stock >= 0
    assert product.category
    assert product.is_active is True
    assert str(product) == product.name


@pytest.mark.django_db
def test_product_unique_name():
    """Test product name must be unique"""
    ProductNewFactory(name="Unique Product")
    with pytest.raises(Exception):  # IntegrityError for unique constraint
        ProductNewFactory(name="Unique Product")


@pytest.mark.django_db
def test_product_category_relationship():
    """Test product-category foreign key relationship"""
    category = CategoryFactory(name="Electronics")
    product = ProductNewFactory(category=category, name="Laptop")
    
    assert product.category == category
    assert product in category.products.all()


@pytest.mark.django_db
def test_product_ordering():
    """Test products are ordered by name"""
    prod_z = ProductNewFactory(name="Z Product")
    prod_a = ProductNewFactory(name="A Product")
    prod_m = ProductNewFactory(name="M Product")
    
    products = ProductNew.objects.all()
    assert products[0].name == "A Product"
    assert products[1].name == "M Product"
    assert products[2].name == "Z Product"


# Category Serializer Tests
@pytest.mark.django_db
def test_category_serialization():
    """Test category data is properly serialized"""
    category = CategoryFactory(name="Test Category", description="Test Description")
    serializer = CategorySerializer(category)
    
    data = serializer.data
    assert data['name'] == "Test Category"
    assert data['description'] == "Test Description"
    assert data['is_active'] is True


@pytest.mark.django_db
def test_category_deserialization_valid():
    """Test valid category data can be deserialized"""
    data = {
        'name': 'Valid Category',
        'description': 'Valid description',
        'is_active': True
    }
    serializer = CategorySerializer(data=data)
    assert serializer.is_valid()


@pytest.mark.django_db
def test_category_name_validation_with_special_chars():
    """Test category name validation rejects special characters"""
    data = {
        'name': 'Invalid@Category!',
        'description': 'Valid description'
    }
    serializer = CategorySerializer(data=data)
    assert not serializer.is_valid()
    assert 'name' in serializer.errors


@pytest.mark.django_db
def test_category_empty_description_validation():
    """Test category description validation rejects empty values"""
    data = {
        'name': 'Valid Category',
        'description': ''
    }
    serializer = CategorySerializer(data=data)
    assert not serializer.is_valid()
    assert 'description' in serializer.errors


# Product Serializer Tests
@pytest.mark.django_db
def test_product_serialization():
    """Test product data is properly serialized"""
    category = CategoryFactory(name="Electronics")
    product = ProductNewFactory(
        name="Test Product",
        price=Decimal("99.99"),
        category=category
    )
    serializer = ProductSerializer(product)
    
    data = serializer.data
    assert data['name'] == "Test Product"
    assert Decimal(data['price']) == Decimal("99.99")
    assert data['category_name'] == "Electronics"
    assert data['is_active'] is True


@pytest.mark.django_db
def test_product_deserialization_valid():
    """Test valid product data can be deserialized"""
    category = CategoryFactory()
    data = {
        'name': 'Valid Product',
        'description': 'Valid description',
        'price': '99.99',
        'stock': 10,
        'category': category.id
    }
    serializer = ProductSerializer(data=data)
    assert serializer.is_valid()


# Category API View Tests
@pytest.mark.django_db
def test_get_categories_list():
    """Test GET /categories/ returns list of active categories"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    active_cat = CategoryFactory(is_active=True)
    inactive_cat = CategoryFactory(is_active=False)
    
    url = reverse('category_list')
    response = client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['name'] == active_cat.name


@pytest.mark.django_db
def test_get_category_detail():
    """Test GET /categories/{id}/ returns category details"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    category = CategoryFactory()
    
    url = reverse('get_category', kwargs={'pk': category.id})
    response = client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == category.name


@pytest.mark.django_db
def test_create_category_valid():
    """Test POST /categories/ creates new category"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    data = {
        'name': 'New Category',
        'description': 'New description',
        'is_active': True
    }
    
    url = reverse('create_category')
    response = client.post(url, data)
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['message'] == "Category created successfully"
    assert Catergory.objects.filter(name='New Category').exists()


@pytest.mark.django_db
def test_create_category_invalid():
    """Test POST /categories/ with invalid data returns error"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    data = {
        'name': 'Invalid@Category!',
        'description': ''
    }
    
    url = reverse('create_category')
    response = client.post(url, data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_update_category():
    """Test PUT /categories/{id}/ updates category"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    category = CategoryFactory()
    data = {
        'name': 'Updated Category',
        'description': 'Updated description',
        'is_active': True
    }
    
    url = reverse('update_category', kwargs={'pk': category.id})
    response = client.put(url, data)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == "Category updated successfully"
    
    category.refresh_from_db()
    assert category.name == 'Updated Category'


@pytest.mark.django_db
def test_delete_category_soft_delete():
    """Test DELETE /categories/{id}/ marks category as inactive"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    category = CategoryFactory(is_active=True)
    
    url = reverse('delete_category', kwargs={'pk': category.id})
    response = client.delete(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == 'Category successfully marked as inactive!'
    
    category.refresh_from_db()
    assert category.is_active is False


@pytest.mark.django_db
def test_activate_category():
    """Test POST /categories/{id}/activate_category/ reactivates category"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    category = CategoryFactory(is_active=False)
    
    url = reverse('activate_category', kwargs={'pk': category.id})
    response = client.post(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == 'Category successfully reactivated!'
    
    category.refresh_from_db()
    assert category.is_active is True


@pytest.mark.django_db
def test_category_unauthenticated_access_denied():
    """Test unauthenticated requests are denied"""
    client = APIClient()
    category = CategoryFactory()
    
    url = reverse('category_list')
    response = client.get(url)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Product API View Tests
@pytest.mark.django_db
def test_get_products_list_paginated():
    """Test GET /products/ returns paginated list of active products"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    category = CategoryFactory()
    # Create 15 products to test pagination (page_size=10)
    for i in range(15):
        ProductNewFactory(category=category, is_active=True)
    
    url = reverse('product_list')
    response = client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data
    assert len(response.data['results']) == 10  # page_size from view
    assert response.data['count'] == 15


@pytest.mark.django_db
def test_get_product_detail():
    """Test GET /products/{id}/ returns product details"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    category = CategoryFactory(name="Electronics")
    product = ProductNewFactory(category=category)
    
    url = reverse('get_product', kwargs={'pk': product.id})
    response = client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == product.name
    assert response.data['category_name'] == "Electronics"


@pytest.mark.django_db
def test_create_product_valid():
    """Test POST /products/ creates new product"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    category = CategoryFactory()
    data = {
        'name': 'New Product',
        'description': 'New description',
        'price': '99.99',
        'stock': 10,
        'category': category.id
    }
    
    url = reverse('create_product')
    response = client.post(url, data)
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['message'] == "Product created successfully"
    assert ProductNew.objects.filter(name='New Product').exists()


@pytest.mark.django_db
def test_create_product_invalid():
    """Test POST /products/ with invalid data returns error"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    data = {
        'name': 'New Product',
        'price': 'invalid-price',
        'stock': -5  # Invalid negative stock
    }
    
    url = reverse('create_product')
    response = client.post(url, data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_update_product():
    """Test PUT /products/{id}/ updates product"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    product = ProductNewFactory()
    data = {
        'name': 'Updated Product',
        'description': 'Updated description',
        'price': '199.99',
        'stock': 20,
        'category': product.category.id
    }
    
    url = reverse('update_product', kwargs={'pk': product.id})
    response = client.put(url, data)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == "Product updated successfully"
    
    product.refresh_from_db()
    assert product.name == 'Updated Product'
    assert product.price == Decimal('199.99')


@pytest.mark.django_db
def test_delete_product_soft_delete():
    """Test DELETE /products/{id}/ marks product as inactive"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    product = ProductNewFactory(is_active=True)
    
    url = reverse('delete_product', kwargs={'pk': product.id})
    response = client.delete(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == 'Product successfully marked as inactive!'
    
    product.refresh_from_db()
    assert product.is_active is False


@pytest.mark.django_db
def test_activate_product():
    """Test POST /products/{id}/activate_product/ reactivates product"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    product = ProductNewFactory(is_active=False)
    
    url = reverse('activate_product', kwargs={'pk': product.id})
    response = client.post(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == 'Product successfully reactivated!'
    
    product.refresh_from_db()
    assert product.is_active is True


@pytest.mark.django_db
def test_product_not_found():
    """Test accessing non-existent product returns 404"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    url = reverse('get_product', kwargs={'pk': 99999})
    response = client.get(url)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_product_unauthenticated_access_denied():
    """Test unauthenticated requests are denied"""
    client = APIClient()
    product = ProductNewFactory()
    
    url = reverse('product_list')
    response = client.get(url)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# File Upload Tests
@pytest.mark.django_db
def test_file_upload_no_file():
    """Test file upload without providing file returns error"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    url = reverse('upload_file')
    response = client.post(url, {})
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'No file provided' in response.data['error']


@pytest.mark.django_db
def test_file_upload_size_limit():
    """Test file upload with oversized file returns error"""
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    
    # Create a mock file that's too large (>2MB)
    large_file = io.BytesIO(b'x' * (3 * 1024 * 1024))  # 3MB
    large_file.name = 'large_file.txt'
    
    url = reverse('upload_file')
    response = client.post(url, {'file': large_file})
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'File size exceeds 2MB limit' in response.data['error']
