from django.db import models
from django.utils import timezone

# Create your models here.

class AozoraBook(models.Model):
    """青空文庫の作品情報"""
    book_id = models.CharField('作品ID', max_length=20, unique=True)
    title = models.CharField('作品名', max_length=200)
    author = models.CharField('著者名', max_length=100)
    author_id = models.CharField('著者ID', max_length=20)
    card_url = models.URLField('図書カードURL', max_length=300)
    release_date = models.DateField('公開日', null=True, blank=True)
    access_count = models.IntegerField('アクセス数', default=0)
    description = models.TextField('あらすじ', blank=True)
    ranking = models.IntegerField('ランキング', null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '青空文庫作品'
        verbose_name_plural = '青空文庫作品'
        ordering = ['-access_count', '-ranking']

    def __str__(self):
        return f'{self.title} - {self.author}'
