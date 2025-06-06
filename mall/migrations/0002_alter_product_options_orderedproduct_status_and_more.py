# Generated by Django 5.1 on 2024-10-04 01:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mall', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='product',
            options={'ordering': ['-sales_count'], 'verbose_name': '상품', 'verbose_name_plural': '상품'},
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='status',
            field=models.CharField(choices=[('ORDERED', '주문됨'), ('SHIPPED', '배송 중'), ('DELIVERED', '배송 완료'), ('RETURN_REQUESTED', '반품 요청됨'), ('RETURNED', '반품 완료'), ('REFUNDED', '환불 완료'), ('CANCEL_REQUESTED', '취소 요청됨'), ('CANCELLED', '취소됨')], default='ORDERED', max_length=16),
        ),
        migrations.AddField(
            model_name='product',
            name='keywords',
            field=models.JSONField(default=list, verbose_name='제품 키워드'),
        ),
        migrations.AddField(
            model_name='product',
            name='review_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='product',
            name='review_score',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='product',
            name='sales_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='product',
            name='view_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='comment',
            name='content',
            field=models.TextField(verbose_name='리뷰 내용'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('REQUSETED', '주문 요청'), ('PAID', '결제 완료'), ('PREPARED_PRODUCT', '상품 준비 중'), ('SHIPPED', '배송 중'), ('DELIVERED', '배송 완료'), ('PARTIAL_REFUNDED', '일부 환불 완료'), ('FULL_REFUNDED', '전체 환불 완료'), ('CANCELLED', '주문 취소'), ('CANCEL_REQUESTED', '취소 요청됨')], default='REQUSETED', max_length=16),
        ),
        migrations.CreateModel(
            name='SubCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subcategories', to='mall.category')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='subcategory',
            field=models.ForeignKey(db_constraint=False, default=1, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='mall.subcategory'),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='SubDetailCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('subcategory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sub_detail_categories', to='mall.subcategory')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='sub_detail_category',
            field=models.ForeignKey(db_constraint=False, default=1, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='mall.subdetailcategory'),
            preserve_default=False,
        ),
    ]
