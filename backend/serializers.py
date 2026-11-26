from rest_framework import serializers
from .models import Product, Stock, StockProduct


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class ProductPositionSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product'
    )

    class Meta:
        model = StockProduct
        fields = (
            'id',
            'price',
            'quantity',
        )


class StockSerializer(serializers.ModelSerializer):
    positions = ProductPositionSerializer(many=True)

    class Meta:
        model = Stock
        fields = (
            'id',
            'address',
            'positions',
        )

    def create(self, validated_data):
        positions = validated_data.pop('positions')

        stock = Stock.objects.create(**validated_data)

        for position in positions:
            StockProduct.objects.create(
                stock=stock,
                **position
            )

        return stock

    def update(self, instance, validated_data):
        positions = validated_data.pop('positions', None)

        instance.address = validated_data.get('address', instance.address)
        instance.save()

        if positions is not None:
            instance.positions.all().delete()

            for position in positions:
                StockProduct.objects.create(
                    stock=instance,
                    **position
                )

        return instance
