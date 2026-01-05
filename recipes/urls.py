from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CuisineViewSet, IngredientViewSet, RecipeViewSet

router = DefaultRouter()
router.register(r"cuisines", CuisineViewSet, basename="cuisine")
router.register(r"ingredients", IngredientViewSet, basename="ingredient")
router.register(r"recipes", RecipeViewSet, basename="recipe")


urlpatterns = [
    path("", include(router.urls)),
]
