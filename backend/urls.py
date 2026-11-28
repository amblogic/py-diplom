from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet, ContactViewSet, ShopViewSet, CategoryViewSet,
    ProductViewSet, ParameterViewSet, ProductInfoViewSet, OrderViewSet,
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('contacts', ContactViewSet, basename='contacts')
router.register('shops', ShopViewSet)
router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet)
router.register('parameters', ParameterViewSet)
router.register('product-info', ProductInfoViewSet, basename='product-info')
router.register('orders', OrderViewSet, basename='orders')

urlpatterns = router.urls