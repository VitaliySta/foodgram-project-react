from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipe.models import (
    Favorite,
    Follow,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingList,
    Tag
)
from users.models import User


class CustomUserSerializer(UserSerializer):
    """Сериализатор для модели User."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj.id).exists()


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания объекта класса User."""

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели IngredientRecipe."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""

    author = CustomUserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def get_ingredients(self, obj):
        ingredients = IngredientRecipe.objects.filter(recipe=obj)
        return IngredientRecipeSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingList.objects.filter(user=request.user,
                                           recipe=obj,).exists()


class AddIngredientSerializer(serializers.ModelSerializer):
    """Вспомогательный сериализатор для RecipeCreateSerializer."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и изменения рецептов."""

    author = CustomUserSerializer(read_only=True)
    ingredients = AddIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'ingredients', 'tags', 'image', 'name',
                  'text', 'cooking_time',)

    def validate(self, data):
        tags = data['tags']
        if not tags:
            raise serializers.ValidationError({
                'tags': 'Тег обязателен для заполнения!'
            })
        tags_set = set()
        for tag in tags:
            if tag in tags_set:
                raise serializers.ValidationError({
                    'tags': f'Тег {tag} существует, измените тег!'
                })
            tags_set.add(tag)
        ingredients = data['ingredients']
        ingredients_set = set()
        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': 'Ингредиенты обязателены для заполнения!'
            })
        for ingredient in ingredients:
            ingredient_id = ingredient['id']
            if ingredient_id in ingredients_set:
                raise serializers.ValidationError({
                    'ingredients': f'Ингредиент {ingredient} существует,'
                                   ' измените ингредиент!'
                })
            ingredients_set.add(ingredient_id)
            amount = ingredient['amount']
            if int(amount) < 1:
                raise serializers.ValidationError({
                    'amount': 'Количество должно быть больше 0!'
                })
        cooking_time = data['cooking_time']
        if int(cooking_time) < 1:
            raise serializers.ValidationError({
                'cooking_time': 'Время приготовления должно быть больше 0!'
            })
        return data

    def add_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create([IngredientRecipe(
            recipe=recipe,
            ingredient=ingredient['id'],
            amount=ingredient['amount'],
        ) for ingredient in ingredients])

    def add_tags(self, tags, recipe):
        for tag in tags:
            recipe.tags.add(tag)

    def create(self, validated_data):
        author = self.context.get('request').user
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=author, **validated_data)
        self.add_tags(tags, recipe)
        self.add_ingredients(ingredients, recipe)
        return recipe

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeSerializer(instance, context=context).data

    def update(self, recipe, validated_data):
        recipe.tags.clear()
        IngredientRecipe.objects.filter(recipe=recipe).delete()
        self.add_tags(validated_data.pop('tags'), recipe)
        self.add_ingredients(validated_data.pop('ingredients'), recipe)
        return super().update(recipe, validated_data)


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Вспомогательный сериализатор для FollowSerializer, FavoriteSerializer и
    ShoppingListSerializer
    """

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(CustomUserSerializer):
    """Сериализатор для модели Follow."""

    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count',)

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return RecipeShortSerializer(recipes, many=True).data

    @staticmethod
    def get_recipes_count(obj):
        return obj.recipes.count()


class FavoriteSerializer(RecipeShortSerializer):
    """Сериализатор для модели Favorite."""

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeShortSerializer(instance.recipe, context=context).data


class ShoppingListSerializer(RecipeShortSerializer):
    """Сериализатор для модели ShoppingList."""

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeShortSerializer(instance.recipe, context=context).data
