# Generated by Django 5.1.6 on 2025-02-21 21:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0006_remove_bookclub_creator_remove_bookclub_current_book_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='summary',
            field=models.TextField(blank=True, null=True),
        ),
    ]
