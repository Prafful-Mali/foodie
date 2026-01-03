from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CuisineViewSet

router = DefaultRouter()
router.register(r"cuisines", CuisineViewSet, basename="cuisine")

urlpatterns = [
    path("", include(router.urls)),
]
