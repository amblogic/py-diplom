from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
import yaml
from urllib.request import urlopen

from rest_framework.decorators import api_view, permission_classes

from .models import (
    Shop, Category, Product, ProductInfo, Parameter,
    Order, OrderItem, Contact,
)
from .serializers import (
    UserSerializer, LoginSerializer, ContactSerializer,
    ShopSerializer, CategorySerializer, ProductSerializer,
    ParameterSerializer, ProductInfoSerializer, OrderSerializer,
)


class UserViewSet(viewsets.GenericViewSet):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [AllowAny]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


class ParameterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer
    permission_classes = [AllowAny]


class ProductInfoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductInfoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = ProductInfo.objects.all()
        shop_id = self.request.query_params.get('shop_id')
        category_id = self.request.query_params.get('category_id')
        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        if category_id:
            qs = qs.filter(product__category_id=category_id)
        return qs


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-dt')

    def _basket(self):
        basket, _ = Order.objects.get_or_create(user=self.request.user, status='basket')
        return basket

    @action(detail=False, methods=['get', 'post', 'put', 'delete'])
    def basket(self, request):
        basket = self._basket()

        if request.method == 'GET':
            return Response(self.get_serializer(basket).data)

        if request.method == 'POST':
            for item in request.data.get('items', []):
                product_info = ProductInfo.objects.get(id=item['product_info'])
                OrderItem.objects.update_or_create(
                    order=basket,
                    product_info=product_info,
                    defaults={'quantity': item['quantity']},
                )
            return Response(self.get_serializer(basket).data,
                            status=status.HTTP_201_CREATED)

        if request.method == 'PUT':
            basket.items.all().delete()
            for item in request.data.get('items', []):
                product_info = ProductInfo.objects.get(id=item['product_info'])
                OrderItem.objects.create(
                    order=basket,
                    product_info=product_info,
                    quantity=item['quantity'],
                )
            return Response(self.get_serializer(basket).data)

        product_info_id = request.data.get('product_info_id')
        basket.items.filter(product_info_id=product_info_id).delete()
        return Response(self.get_serializer(basket).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        order = self.get_object()
        if not order.items.exists():
            return Response({'error': 'Заказ пуст'},
                            status=status.HTTP_400_BAD_REQUEST)
        order.status = 'new'
        order.save()
        return Response(self.get_serializer(order).data)
    
def ping(request):
    return JsonResponse({'status': 'ok', 'message': 'Сервер работает'})



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def partner_update(request):
    # 1. Проверяем, что это магазин
    if request.user.type != 'shop':
        return Response(
            {'Status': False, 'Error': 'Только для магазинов'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # 2. Берём url из запроса
    url = request.data.get('url')
    if not url:
        return Response(
            {'Status': False, 'Error': 'Не передан url'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Скачиваем и парсим YAML
    stream = urlopen(url).read()
    data = yaml.safe_load(stream)

    # 4. Создаём магазин
    shop, _ = Shop.objects.get_or_create(name=data['shop'])

    # 5. Категории
    for cat in data['categories']:
        category, _ = Category.objects.get_or_create(
            id=cat['id'],
            defaults={'name': cat['name']},
        )
        category.shops.add(shop)

    # 6. Удаляем старый прайс этого магазина
    ProductInfo.objects.filter(shop=shop).delete()

    # 7. Товары
    for item in data['goods']:
        product, _ = Product.objects.get_or_create(
            name=item['name'],
            category_id=item['category'],
        )
        product_info = ProductInfo.objects.create(
            product=product,
            shop=shop,
            external_id=item['id'],
            model=item['model'],
            name=item['name'],
            price=item['price'],
            price_rrc=item['price_rrc'],
            quantity=item['quantity'],
        )

        # 8. Параметры
        for name, value in item.get('parameters', {}).items():
            parameter, _ = Parameter.objects.get_or_create(name=name)
            ProductParameter.objects.create(
                product_info=product_info,
                parameter=parameter,
                value=str(value),
            )

    return Response({'Status': True})