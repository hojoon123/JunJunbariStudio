from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image
from .models import ProductImage


@receiver(post_save, sender=ProductImage)
def resize_image(sender, instance, **kwargs):
    image_path = instance.image.path
    with Image.open(image_path) as img:
        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(image_path)
