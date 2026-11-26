from rest_framework.routers import DefaultRouter

from backend.views import ProductViewSet, StockViewSet

router = DefaultRouter()
router.register("products", ProductViewSet)
router.register("stocks", StockViewSet)

urlpatterns = router.urls
