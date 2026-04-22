#using REST framework serializers to handle producer registration and product management
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import ProducerProfile, Product

User = get_user_model()


class ProducerRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    producer_name = serializers.CharField(max_length=200)
    contact_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=30)
    address = serializers.CharField()
    postcode = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, label="Confirm password")

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        
        try:
            validate_password(data['password'])
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        
        producer_data = {
            "producer_name": validated_data.pop("producer_name"),
            "contact_name": validated_data.pop("contact_name"),
            "phone": validated_data.pop("phone"),
            "address": validated_data.pop("address"),
            "postcode": validated_data.pop("postcode"),
        }

        email = validated_data['email'].strip().lower()
        password = validated_data['password']
        
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        ProducerProfile.objects.create(user=user, **producer_data)
        return user


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'price',
            'category',
            'description',
            'allergen_info',
            'organic_certified',
            'harvest_date',
            'stock_quantity',
            'availability_status'
        ]
        
    def create(self, validated_data):
        # The producer is passed in the serializer context, its set here before creating the product.
        validated_data['producer'] = self.context['producer']
        return Product.objects.create(**validated_data)
