from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    Shop, Category, Product, ProductInfo, Parameter,
    ProductParameter, Order, OrderItem, Contact,
)

User = get_user_model()


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'phone')
        read_only_fields = ('id',)


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, read_only=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'id', 'first_name', 'last_name', 'email', 'username',
            'company', 'position', 'password', 'password_confirm', 'contacts',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password': 'Пароли не совпадают'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Неверный email или пароль')
        if not user.is_active:
            raise serializers.ValidationError('Пользователь заблокирован')
        attrs['user'] = user
        return attrs


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'url')
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    shops = ShopSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'shops')
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category')
        read_only_fields = ('id',)


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source='parameter.name')

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value')


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    shop = ShopSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = (
            'id', 'product', 'shop', 'name', 'quantity',
            'price', 'price_rrc', 'product_parameters',
        )
        read_only_fields = ('id',)


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ('id', 'name')
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'total_sum')
        read_only_fields = ('id',)

    def get_total_sum(self, obj):
        return obj.quantity * obj.product_info.price


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'dt', 'status', 'items', 'total_sum')
        read_only_fields = ('id', 'dt', 'status')

    def get_total_sum(self, obj):
        return sum(item.quantity * item.product_info.price for item in obj.items.all())


class OrderItemCreateSerializer(serializers.Serializer):
    product_info = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_info(self, value):
        if not ProductInfo.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Товар не найден')
        return value