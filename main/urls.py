from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    # API エンドポイント（/api/ プレフィックス付きでアクセス）
    path('health/', views.health_check, name='health'),
    path('popular-books/', views.popular_books_api, name='popular_books_api'),
    path('weather/', views.weather_api, name='weather_api'),
    path('recommend/', views.recommend_books_api, name='recommend_books_api'),
    
    # Webページ
    path('preview/<str:book_id>/', views.book_preview, name='book_preview'),
]
