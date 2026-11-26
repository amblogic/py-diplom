from rest_framework.viewsets import ModelViewSet
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from backend.models import Product, Stock
from backend.serializers import ProductSerializer, StockSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination

    queryset = Product.objects.all()


class StockViewSet(ModelViewSet):
    serializer_class = StockSerializer
    pagination_class = StandardResultsSetPagination
    queryset = Stock.objects.all()
