from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Shop, Category, ProductInfo, Order, OrderItem, Contact
from .serializers import (
    UserSerializer, LoginSerializer, ContactSerializer,
    ShopSerializer, CategorySerializer, ProductInfoSerializer,
    OrderSerializer, OrderItemCreateSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {'token': token.key, 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user_id': user.id, 'email': user.email})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)


class ShopView(generics.ListAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = (permissions.AllowAny,)


class CategoryView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)


class ProductInfoView(generics.ListAPIView):
    """Список товаров с фильтрами по магазину/категории и поиском по названию."""
    serializer_class = ProductInfoSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = (SearchFilter,)
    search_fields = ('product__name', 'shop__name', 'name')

    def get_queryset(self):
        qs = ProductInfo.objects.select_related('product', 'shop') \
                                .prefetch_related('product_parameters__parameter')
        shop_id = self.request.query_params.get('shop_id')
        category_id = self.request.query_params.get('category_id')
        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        if category_id:
            qs = qs.filter(product__category_id=category_id)
        return qs


# ---------------- Корзина ----------------

class BasketView(APIView):
    """
    GET    — показать корзину
    POST   — добавить позиции: {"items": [{"product_info": 1, "quantity": 2}]}
    PUT    — заменить позиции
    DELETE — удалить позицию: {"product_info_id": 1}
    """

    def _get_basket(self, request):
        basket, _ = Order.objects.get_or_create(user=request.user, status='basket')
        return basket

    def get(self, request):
        return Response(OrderSerializer(self._get_basket(request)).data)

    def post(self, request):
        items = request.data.get('items')
        if not items:
            return Response({'error': 'Поле items обязательно'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderItemCreateSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)

        basket = self._get_basket(request)
        with transaction.atomic():
            for item in serializer.validated_data:
                product_info = ProductInfo.objects.select_related('product').get(pk=item['product_info'])
                if item['quantity'] > product_info.quantity:
                    return Response(
                        {'error': f'Недостаточно товара «{product_info.product.name}»'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                OrderItem.objects.update_or_create(
                    order=basket,
                    product_info=product_info,
                    defaults={'quantity': item['quantity']},
                )
        return Response(OrderSerializer(basket).data, status=status.HTTP_201_CREATED)

    def put(self, request):
        items = request.data.get('items')
        if not items:
            return Response({'error': 'Поле items обязательно'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderItemCreateSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)

        basket = self._get_basket(request)
        with transaction.atomic():
            basket.items.all().delete()
            for item in serializer.validated_data:
                product_info = ProductInfo.objects.get(pk=item['product_info'])
                OrderItem.objects.create(
                    order=basket, product_info=product_info, quantity=item['quantity'],
                )
        return Response(OrderSerializer(basket).data)

    def delete(self, request):
        product_info_id = request.data.get('product_info_id')
        if not product_info_id:
            return Response({'error': 'Поле product_info_id обязательно'},
                            status=status.HTTP_400_BAD_REQUEST)
        basket = self._get_basket(request)
        deleted, _ = basket.items.filter(product_info_id=product_info_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(basket).data)


class OrderView(generics.ListAPIView):
    """Список оформленных заказов пользователя (без корзины)."""
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(status='basket').order_by('-dt')


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderConfirmView(APIView):
    """Превращает корзину в оформленный заказ и списывает остатки."""
    def post(self, request):
        basket = Order.objects.filter(user=request.user, status='basket').first()
        if not basket or not basket.items.exists():
            return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

        contact_id = request.data.get('contact_id')
        if contact_id and not Contact.objects.filter(pk=contact_id, user=request.user).exists():
            return Response({'error': 'Контакт не найден'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for item in basket.items.select_related('product_info__product'):
                if item.quantity > item.product_info.quantity:
                    return Response(
                        {'error': f'Недостаточно товара «{item.product_info.product.name}»'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            for item in basket.items.select_related('product_info'):
                item.product_info.quantity -= item.quantity
                item.product_info.save(update_fields=['quantity'])
            basket.status = 'new'
            basket.save(update_fields=['status'])

        return Response(OrderSerializer(basket).data)


class OrderCancelView(APIView):
    """Отмена заказа."""
    def delete(self, request, pk):
        order = Order.objects.filter(pk=pk, user=request.user).first()
        if not order:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if order.status in ('sent', 'delivered', 'canceled'):
            return Response({'error': 'Заказ нельзя отменить'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'canceled'
        order.save(update_fields=['status'])
        return Response(status=status.HTTP_204_NO_CONTENT)