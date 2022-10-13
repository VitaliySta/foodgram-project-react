from collections import Counter

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

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

from .filters import IngredientSearchFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnlyPermission
from .serializers import (
    CustomUserSerializer,
    FavoriteSerializer,
    FollowSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
    ShoppingListSerializer,
    TagSerializer
)


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с обьектами класса User и подписки на авторов."""

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated, )
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(follow__user=self.request.user)
        if queryset:
            pages = self.paginate_queryset(queryset)
            serializer = FollowSerializer(pages, many=True,
                                          context={'request': request})
            return self.get_paginated_response(serializer.data)
        return Response('Вы ни на кого не подписаны.',
                        status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        change_subscription = Follow.objects.filter(
            user=user.id, author=author.id
        )
        if request.method == 'POST':
            if user == author:
                return Response('На себя подписываться нельзя!',
                                status=status.HTTP_400_BAD_REQUEST)
            if change_subscription.exists():
                return Response(f'Вы уже подписаны на {author}',
                                status=status.HTTP_400_BAD_REQUEST)
            subscribe = Follow.objects.create(
                user=user,
                author=author
            )
            subscribe.save()
            return Response(f'Вы подписались на {author}',
                            status=status.HTTP_201_CREATED)
        if change_subscription.exists():
            change_subscription.delete()
            return Response(f'Вы больше не подписаны на {author}',
                            status=status.HTTP_204_NO_CONTENT)
        return Response(f'Вы не подписаны на {author}',
                        status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет работы с обьектами класса Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с обьектами класса Ingredien."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientSearchFilter
    search_fields = ('^name', )
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с обьектами класса Recipe."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnlyPermission,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return RecipeCreateSerializer

    @staticmethod
    def create_object(request, pk, serializers):
        data = {'user': request.user.id, 'recipe': pk}
        serializer = serializers(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_object(request, pk, model):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        object = get_object_or_404(model, user=user, recipe=recipe)
        object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.create_object(request=request, pk=pk,
                                      serializers=FavoriteSerializer)
        return self.delete_object(request=request, pk=pk, model=Favorite)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.create_object(request=request, pk=pk,
                                      serializers=ShoppingListSerializer)
        return self.delete_object(request=request, pk=pk, model=ShoppingList)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, user):
        ingredients = IngredientRecipe.objects.filter(
            recipe__shop_list__user=user.user
        )
        compressed_ingredients = Counter()
        for ing in ingredients:
            compressed_ingredients[
                (ing.ingredient.name, ing.ingredient.measurement_unit)
            ] += ing.amount
        shopping_cart = ([
            f"- {name}: {amount} {measurement_unit}\n"
            for (name, measurement_unit), amount
            in compressed_ingredients.items()
        ])
        filename = 'shopping-list.txt'
        response = HttpResponse(shopping_cart, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
