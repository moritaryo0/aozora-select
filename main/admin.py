from django.contrib import admin
from .models import AozoraBook

# Register your models here.

@admin.register(AozoraBook)
class AozoraBookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'ranking', 'access_count', 'updated_at']
    list_filter = ['author', 'updated_at']
    search_fields = ['title', 'author', 'description']
    ordering = ['ranking', '-access_count']
    readonly_fields = ['created_at', 'updated_at']
