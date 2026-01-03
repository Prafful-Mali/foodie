from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CuisineViewSet, IngredientViewSet

router = DefaultRouter()
router.register(r"cuisines", CuisineViewSet, basename="cuisine")
router.register(r"ingredients", IngredientViewSet, basename="ingredient")


urlpatterns = [
    path("", include(router.urls)),
]
