# Generated by Django 5.1.4 on 2024-12-09 12:27

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('literatur', '0009_category_alter_books_kategori'),
    ]

    operations = [
        migrations.AlterField(
            model_name='books',
            name='id',
            field=models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='books',
            name='pdf_full',
            field=models.FileField(blank=True, null=True, upload_to='pdf_full', verbose_name='File PDF Full'),
        ),
        migrations.AlterField(
            model_name='books',
            name='pdf_prev',
            field=models.FileField(blank=True, null=True, upload_to='pdf_prev', verbose_name='File PDF Preview'),
        ),
    ]
