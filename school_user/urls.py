from django.urls import path
from .views import CustomTokenObtainPairView

urlpatterns = [
    path('', CustomTokenObtainPairView.as_view(), name='token_by_email'),
]
