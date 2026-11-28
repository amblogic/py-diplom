# backend/models.py
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

class UserManager(BaseUserManager):
    """Миксин для управления пользователями"""
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Стандартная модель пользователей"""
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='buyer')
    
  
class Shop(models.Model):
    """магазин, который может быть связан с несколькими категориями товаров."""
    name = models.CharField(max_length=50, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка', null=True, blank=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Список магазинов'
        ordering = ('-name',)

    def __str__(self):
        return self.name
    
class Category(models.Model):
    """Категория товаров. У одной категории может быть несколько магазинов"""
    name = models.CharField(max_length=40, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Список категорий'
        ordering = ('-name',)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    """Базовый товар, который относится к определенной категории."""
    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=80, verbose_name='Наименование')
    external_id = models.PositiveIntegerField(verbose_name='ID товара у поставщика', null=True, blank=True)
    model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
    description = models.TextField(verbose_name='Описание', blank=True)
    
    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Список продуктов'
        ordering = ('-name',)

    def __str__(self):
        return self.name
    
class ProductInfo(models.Model):
    """модель для связи товара с магазином. Содержит конкретные сведения о товаре"""
    product = models.ForeignKey(Product, verbose_name='Продукт', on_delete=models.CASCADE, related_name='product_infos')
    shop = models.ForeignKey(Shop, verbose_name='Магазин', on_delete=models.CASCADE, related_name='product_infos')
    name = models.CharField(max_length=80, verbose_name='Наименование', blank=True)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Рекомендуемая розничная цена')

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = 'Информационный список о продуктах'

    def __str__(self):
        return f'{self.product.name} - {self.shop.name}'
    
class Parameter(models.Model):
    """Справочник параметров товаров"""
    name = models.CharField(max_length=40, verbose_name='Название')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Список параметров'
        ordering = ('-name',)

    def __str__(self):
        return self.name
    
class ProductParameter(models.Model):
    """Связывает информацию о товаре (ProductInfo) с параметром (Parameter)"""
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте', on_delete=models.CASCADE, related_name='product_parameters')
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', on_delete=models.CASCADE, related_name='product_parameters')
    value = models.CharField(max_length=100, verbose_name='Значение')

    class Meta:
        verbose_name = 'Параметр продукта'
        verbose_name_plural = 'Список параметров продуктов'

    def __str__(self):
        return f'{self.product_info} - {self.parameter.name}: {self.value}'
    
class Contact(models.Model):
    """Контактная информация о пользователе."""
    user = models.ForeignKey(
        User, verbose_name='Пользователь',
        on_delete=models.CASCADE, related_name='contacts',
    )
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    address = models.CharField(max_length=200, verbose_name='Адрес', blank=True, default='')
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Список контактов'

    def __str__(self):
        return f'{self.city}, {self.street}, {self.phone}'

class Order(models.Model):
    """Модель заказа"""
    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='orders')
    dt = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    status = models.CharField(max_length=20, choices=STATE_CHOICES, verbose_name='Статус')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Список заказов'
        ordering = ('-dt',)

    def __str__(self):
        return f'Заказ №{self.id} от {self.user.email}'

class OrderItem(models.Model):
    """Позиция в заказе"""
    order = models.ForeignKey(
        Order, verbose_name='Заказ',
        on_delete=models.CASCADE, related_name='items',
    )
    product_info = models.ForeignKey(
        ProductInfo, verbose_name='Информация о продукте',
        on_delete=models.CASCADE, related_name='order_items',
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'

    def __str__(self):
        return f'{self.product_info.product.name} x {self.quantity}'
