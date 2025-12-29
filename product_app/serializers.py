from rest_framework import serializers
from .models import ProductNew, Catergory
import re

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)  # Add category name

    class Meta:
        model = ProductNew
        fields = ['id', 'name', 'description', 'price', 'stock', 'image_url', 'created_at', 'updated_at', 'category', 'category_name', 'is_active']
        
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Catergory
        fields = ['id', 'name', 'description', 'is_active']
        
    def validate_name(self, value):
        # Ensure the name does not contain special characters
        if not re.match("^[a-zA-Z0-9 ]*$", value):
            raise serializers.ValidationError("Name must not contain special characters.")
        return value

    def validate_description(self, value):

        if not value:
            raise serializers.ValidationError("Description cannot be empty.")
        return value
        