from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    email = models.EmailField(blank=True, null=True)  # emailをオプショナルに
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(max_length=500, blank=True, help_text="自己紹介")
    favorite_genre = models.CharField(max_length=100, blank=True, help_text="好きなジャンル")
    reading_time_preference = models.CharField(
        max_length=20, 
        blank=True,
        help_text="読書時間の好み（朝、昼、夜など）"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # usernameで認証するように変更
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'