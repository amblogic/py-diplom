from django.urls import path

from .views import (
    RegisterView, LoginView, LogoutView,
    ContactView, ContactDetailView,
    ShopView, CategoryView, ProductInfoView,
    BasketView, OrderView, OrderDetailView, OrderConfirmView, OrderCancelView,
)

urlpatterns = [
    path('register', RegisterView.as_view()),
    path('login', LoginView.as_view()),
    path('logout', LogoutView.as_view()),

    path('contacts', ContactView.as_view()),
    path('contacts/<int:pk>', ContactDetailView.as_view()),

    path('shops', ShopView.as_view()),
    path('categories', CategoryView.as_view()),
    path('products', ProductInfoView.as_view()),

    path('basket', BasketView.as_view()),

    path('orders', OrderView.as_view()),
    path('orders/confirm', OrderConfirmView.as_view()),
    path('orders/<int:pk>', OrderDetailView.as_view()),
    path('orders/<int:pk>/cancel', OrderCancelView.as_view()),
]