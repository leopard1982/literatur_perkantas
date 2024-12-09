# Generated by Django 5.1.3 on 2024-12-07 01:24

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('literatur', '0002_books_discount_books_is_bestseller_books_is_discount_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='userdetail',
            name='id_customer',
            field=models.UUIDField(auto_created=True, default=uuid.UUID('8eb82113-b02a-4aac-ac77-931ddc543d4c'), editable=False),
        ),
        migrations.AlterField(
            model_name='bookreview',
            name='id',
            field=models.UUIDField(auto_created=True, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='books',
            name='id',
            field=models.UUIDField(auto_created=True, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='customerbookmark',
            name='id_bookmark',
            field=models.UUIDField(auto_created=True, editable=False, primary_key=True, serialize=False),
        ),
        migrations.CreateModel(
            name='PageReview',
            fields=[
                ('id', models.UUIDField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ('review', models.CharField(blank=True, max_length=400, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
