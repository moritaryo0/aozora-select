"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from main import views
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('main.urls')),
    
    # ヘルスチェックエンドポイント
    path('health/', views.health_check, name='health_check'),
    
    # メインページ：青空セレクトのウェルカムページ
    path('', views.welcome_page, name='welcome'),
    
    # 青空文庫関連ページ
    path('popular-books/', views.popular_books_view, name='popular_books'),
    path('preview/<str:book_id>/', views.book_preview, name='book_preview'),
    
    # 認証関連HTMLページ（名前空間の重複を避けるため直接指定）
    path('accounts/my-page/', account_views.my_page, name='my_page'),
    path('accounts/register-page/', account_views.register_page, name='register_page'),
    
    # 開発・テスト用ページ
    path('test/', views.api_test_page, name='api_test'),
    path('login-test/', views.login_test_page, name='login_test'),
]
