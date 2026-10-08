"""Imágenes de producto: validación y reducción al cargarlas.

Se acepta JPG, PNG o WebP de hasta ``MAX_UPLOAD_BYTES``; se corrige la orientación, se reduce a
``MAX_SIDE`` px por lado y se guarda como WebP comprimido (normalmente < 40 KB), para que las
pantallas de venta con muchos productos carguen rápido.
"""
import os
import re
from io import BytesIO

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 2 * 1024 * 1024      # lo máximo que se acepta subir
MAX_SIDE = 400                          # lado máximo (px) de las imágenes de producto
USER_MAX_SIDE = 256                     # lado máximo (px) de las fotos de usuario (se ven a ~34 px en el menú)
MAX_SOURCE_PIXELS = 25_000_000          # evita imágenes gigantes que agotan la memoria
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
WEBP_QUALITY = 80


def _safe_stem(name):
    stem = os.path.splitext(os.path.basename(name or 'producto'))[0]
    stem = re.sub(r'[^A-Za-z0-9_-]+', '-', stem).strip('-')[:50]
    return stem or 'producto'


def shrink_image(file_obj, name=None, max_side=MAX_SIDE):
    """Valida la imagen y devuelve un ``ContentFile`` WebP de máximo ``max_side`` px por lado.

    Lanza ``ValidationError`` con un mensaje claro si no es una imagen válida o es muy pesada.
    """
    size = getattr(file_obj, 'size', None)
    if size is not None and size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f'La imagen pesa {size / 1024 / 1024:.1f} MB y el máximo es {MAX_UPLOAD_BYTES // 1024 // 1024} MB. '
            'Use una imagen más pequeña.')
    try:
        file_obj.seek(0)
        image = Image.open(file_obj)
        image.verify()                      # detecta archivos corruptos o que no son imagen
        file_obj.seek(0)
        image = Image.open(file_obj)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError('El archivo no es una imagen válida. Use JPG, PNG o WebP.')
    if image.format not in ALLOWED_FORMATS:
        raise ValidationError('Formato no permitido. Use una imagen JPG, PNG o WebP.')
    if image.width * image.height > MAX_SOURCE_PIXELS:
        raise ValidationError('La imagen tiene demasiados píxeles. Reduzca su tamaño antes de subirla.')

    image = ImageOps.exif_transpose(image)
    has_alpha = image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)
    image = image.convert('RGBA' if has_alpha else 'RGB')
    image.thumbnail((max_side, max_side), Image.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format='WEBP', quality=WEBP_QUALITY, method=4)
    return ContentFile(buffer.getvalue(), name=f'{_safe_stem(name or getattr(file_obj, "name", ""))}.webp')


class ProductImageField(forms.ImageField):
    """ImageField que revisa el peso ANTES de validar la imagen, para dar el mensaje correcto."""

    def to_python(self, data):
        size = getattr(data, 'size', None)
        if size is not None and size > MAX_UPLOAD_BYTES:
            raise ValidationError(
                f'La imagen pesa {size / 1024 / 1024:.1f} MB y el máximo es {MAX_UPLOAD_BYTES // 1024 // 1024} MB. '
                'Use una imagen más pequeña.')
        return super().to_python(data)
