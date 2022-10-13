from django.contrib import admin

from .models import (
    Favorite,
    Follow,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingList,
    Tag
)

admin.site.empty_value_display = 'Значение отсутствует'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Класс настройки раздела тегов"""

    list_display = ('pk', 'name', 'slug')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Класс настройки раздела игредиентов"""

    list_display = ('pk', 'name', 'measurement_unit')
    search_fields = ('name',)


class IngredientRecipeInline(admin.TabularInline):
    """
    Вспомогательный класс, чтобы в классе RecipeAdmin можно было настроивать
    ингредиенты.
    """

    model = IngredientRecipe
    min_num = 1
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Класс настройки раздела рецептов"""

    list_display = ('pk', 'name', 'author', 'get_favorites', 'get_tags',)
    list_filter = ('author', 'name', 'tags')
    search_fields = ('name',)
    inlines = (IngredientRecipeInline,)

    def get_favorites(self, obj):
        return obj.favorites.count()

    get_favorites.short_description = (
        'Количество добавлений рецепта в избранное'
    )

    def get_tags(self, obj):
        return '\n'.join((tag.name for tag in obj.tags.all()))

    get_tags.short_description = 'Тег или список тегов'


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Класс настройки раздела подписки"""

    list_display = ('pk', 'user', 'author')
    search_fields = ('user', 'author')
    list_filter = ('user', 'author')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Класс настройки раздела избранное"""

    list_display = ('pk', 'user', 'recipe')


@admin.register(IngredientRecipe)
class IngredientRecipeAdmin(admin.ModelAdmin):
    """Класс настройки соответствия ингредиентов и рецепта"""

    list_display = ('pk', 'ingredient', 'recipe', 'amount')


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
