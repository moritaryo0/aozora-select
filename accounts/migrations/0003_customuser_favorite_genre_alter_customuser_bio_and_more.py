# Generated by Django 4.2.7 on 2025-07-24 18:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_customuser_options_customuser_bio_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='favorite_genre',
            field=models.CharField(blank=True, help_text='好きなジャンル', max_length=100),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='bio',
            field=models.TextField(blank=True, help_text='自己紹介', max_length=500),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='reading_time_preference',
            field=models.CharField(blank=True, help_text='読書時間の好み（朝、昼、夜など）', max_length=20),
        ),
    ]
