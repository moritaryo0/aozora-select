from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

app_name = 'accounts'

urlpatterns = [
    # JWT認証関連
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('verify/', TokenVerifyView.as_view(), name='verify'),
    path('logout/', views.logout_view, name='logout'),
    path('status/', views.auth_status, name='status'),
    
    # ユーザー管理関連
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # HTMLページ
    path('my-page/', views.my_page, name='my_page'),
    path('register-page/', views.register_page, name='register_page'),
]