import os
from io import BytesIO
from PIL import Image
from datetime import datetime

from django.db import models
from django.db.models import Sum, FloatField
from django.db.models.functions import Coalesce
from django.forms import model_to_dict
from django.core.files.base import ContentFile
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from django.utils import timezone

from config import settings


class BiologicalTargetCategory(models.Model):
    name = models.CharField(max_length=150,unique=True,verbose_name='Nombre')
    description = models.TextField(blank=True,null=True,verbose_name='Descripción')
    is_active = models.BooleanField(default=True,verbose_name='Estado')

    def __str__(self):
        return self.name

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Categoría de Blanco Biológico'
        verbose_name_plural = 'Categorías de Blancos Biológicos'
        default_permissions = ()
        permissions = (
            ('view_biological_target_category', 'Consultar Categorías de Blancos Biológicos'),
            ('add_biological_target_category', 'Crear Categorías de Blancos Biológicos'),
            ('change_biological_target_category', 'Editar Categorías de Blancos Biológicos'),
            ('delete_biological_target_category', 'Eliminar Categorías de Blancos Biológicos'),
        )

class BiologicalTarget(models.Model):
    category = models.ForeignKey(BiologicalTargetCategory,on_delete=models.PROTECT,verbose_name='Categoría')
    code = models.CharField(max_length=50,unique=True,verbose_name='Código')
    name = models.CharField(max_length=150,verbose_name='Nombre')
    scientific_name = models.CharField(max_length=250,blank=True,null=True,verbose_name='Nombre científico')

    # Reglas de negocio
    healthy_bed = models.BooleanField(default=False,verbose_name='Cuadro sano')
    aspirated = models.BooleanField(default=False,verbose_name='Aspirado')
    exclude_aspirated = models.BooleanField(default=False,verbose_name='Excluir aspirado')
    external_trap = models.BooleanField(default=False,verbose_name='Trampa externa')
    internal_trap = models.BooleanField(default=False,verbose_name='Trampa interna')
    cold_room_assurance = models.BooleanField(default=False,verbose_name='Aseguramiento cuarto frío')
    automatic_discard = models.BooleanField(default=False,verbose_name='Descarte automático')
    is_active = models.BooleanField(default=True,verbose_name='Estado')

    def __str__(self):
        return self.name

    def toJSON(self):
        item = model_to_dict(self)

        item['category'] = {
            'id': self.category.id,
            'name': self.category.name
        }

        return item

    class Meta:
        verbose_name = 'Blanco Biológico'
        verbose_name_plural = 'Blancos Biológicos'
        default_permissions = ()
        permissions = (
            ('view_biological_target', 'Consultar Blancos Biológicos'),
            ('add_biological_target', 'Crear Blancos Biológicos'),
            ('change_biological_target', 'Editar Blancos Biológicos'),
            ('delete_biological_target', 'Eliminar Blancos Biológicos'),
        )

class SeverityGrade(models.Model):
    category = models.ForeignKey(
        BiologicalTargetCategory, 
        on_delete=models.CASCADE, 
        related_name='severity_grades',
        verbose_name='Categoría'
    )
    grade_number = models.IntegerField(verbose_name='Grado (Número)')
    name = models.CharField(max_length=50, verbose_name='Nombre')
    
    # Límites numéricos para automatizar los cálculos en frontend / backend
    min_value = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Valor Mínimo') # 0.00, 26.00, 4.00
    max_value = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Valor Máximo') # 3.00, 25.00, 9999.00
    
    description = models.CharField(max_length=250, blank=True, null=True, verbose_name='Descripción Corta') # "0 - 25%" u "0 a 3 insectos"
    is_active = models.BooleanField(default=True, verbose_name='Estado')

    def __str__(self):
        return f"{self.category.name} - {self.name} ({self.description})"

    def toJSON(self):
        item = model_to_dict(self)
        item['category'] = {
            'id': self.category.id,
            'name': self.category.name
        }
        item['min_value'] = float(self.min_value)
        item['max_value'] = float(self.max_value)
        return item

    class Meta:
        verbose_name = 'Grado de Severidad'
        verbose_name_plural = 'Grados de Severidad'
        ordering = ['category', 'grade_number']
        default_permissions = ()
        permissions = (
            ('view_severity_grade', 'Consultar Grados de Severidad'),
            ('add_severity_grade', 'Crear Grados de Severidad'),
            ('change_severity_grade', 'Editar Grados de Severidad'),
            ('delete_severity_grade', 'Eliminar Grados de Severidad'),
        )

class MipeModule(models.Model):
    name = models.CharField(max_length=100,verbose_name='Nombre')
    description = models.CharField(max_length=200,blank=True,null=True,verbose_name='Descripción')
    order = models.PositiveIntegerField(default=1,verbose_name='Orden')
    icon = models.CharField(max_length=100,verbose_name='Icono FontAwesome')
    url_name = models.CharField(max_length=100,unique=True,verbose_name='URL')
    is_active = models.BooleanField(default=True,verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Módulo MIPE'
        verbose_name_plural = 'Módulos MIPE'
        ordering = ['order']
        default_permissions = ()
        permissions = (
            ('add_mipe_module', 'Crear módulos MIPE'),
            ('change_mipe_module', 'Editar módulos MIPE'),
            ('delete_mipe_module', 'Eliminar módulos MIPE'),
            ('view_mipe_module', 'Consultar módulos MIPE'),
        )

    def __str__(self):
        return self.name

    def toJSON(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'order': self.order,
            'icon': self.icon,
            'url_name': self.url_name,
            'is_active': self.is_active,
        }

class Block(models.Model):
    code = models.CharField(max_length=20,unique=True)
    name = models.CharField(max_length=100)
    has_sides = models.BooleanField(default=False,verbose_name='¿Maneja lado A y B?')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Bloque'
        verbose_name_plural = 'Bloques'
        ordering = ['code']
        default_permissions = ()
        permissions = (
            ('view_block', 'Consultar bloques'),
            ('add_block', 'Crear bloques'),
            ('change_block', 'Editar bloques'),
            ('delete_block', 'Eliminar bloques'),
        )

    def __str__(self):
        return f'{self.code} - {self.name}'

    def toJSON(self):

        item = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'has_sides': self.has_sides,
            'is_active': self.is_active,
        }

        return item

class BlockBay(models.Model):
    block = models.ForeignKey(Block,on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    side = models.CharField(max_length=1,choices=(('A', 'Lado A'),('B', 'Lado B'),),blank=True,null=True)
    bed_quantity = models.PositiveIntegerField(default=8,verbose_name='Cantidad de camas')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Nave'
        verbose_name_plural = 'Naves'
        ordering = ['block', 'code']
        default_permissions = ()
        permissions = (
            ('view_block_bay', 'Consultar naves'),
            ('add_block_bay', 'Crear naves'),
            ('change_block_bay', 'Editar naves'),
            ('delete_block_bay', 'Eliminar naves'),
        )

    def __str__(self):

        if self.side:
            return f'{self.block.code} - Nave {self.code} - Lado {self.side}'

        return f'{self.block.code} - Nave {self.code}'

    def toJSON(self):

        item = {
            'id': self.id,
            'block': self.block.name,
            'block_id': self.block.id,
            'code': self.code,
            'side': self.side,
            'side_display': self.get_side_display() if self.side else '',
            'bed_quantity': self.bed_quantity,
            'is_active': self.is_active,
        }

        return item

class Bed(models.Model):
    bay = models.ForeignKey(BlockBay,on_delete=models.CASCADE,related_name='beds')
    number = models.PositiveIntegerField(verbose_name='Número de cama')
    parity = models.CharField(max_length=10,choices=(('odd', 'Impar'),('even', 'Par')))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cama'
        verbose_name_plural = 'Camas'
        ordering = ['bay', 'number']
        default_permissions = ()
        permissions = (
            ('view_bed', 'Consultar camas'),
            ('add_bed', 'Crear camas'),
            ('change_bed', 'Editar camas'),
            ('delete_bed', 'Eliminar camas'),
        )
        unique_together = (
            ('bay', 'number'),
        )

    def __str__(self):
        return f'{self.bay} - Cama {self.number}'

    def toJSON(self):

        item = {
            'id': self.id,
            'bay': str(self.bay),
            'bay_id': self.bay.id,
            'number': self.number,
            'parity': self.parity,
            'parity_display': self.get_parity_display(),
            'is_active': self.is_active,
        }

        return item

class BedSection(models.Model):
    bed = models.ForeignKey(Bed,on_delete=models.CASCADE,related_name='sections')
    number = models.PositiveIntegerField(verbose_name='Número de cuadro')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cuadro de Cama'
        verbose_name_plural = 'Cuadros de Cama'
        ordering = ['bed', 'number']
        default_permissions = ()
        permissions = (
            ('view_bed_section', 'Consultar cuadros de cama'),
            ('add_bed_section', 'Crear cuadros de cama'),
            ('change_bed_section', 'Editar cuadros de cama'),
            ('delete_bed_section', 'Eliminar cuadros de cama'),
        )
        unique_together = (
            ('bed', 'number'),
        )

    def __str__(self):
        return f'{self.bed} - Cuadro {self.number}'

    def toJSON(self):

        item = {
            'id': self.id,
            'bed': str(self.bed),
            'bed_id': self.bed.id,
            'number': self.number,
            'is_active': self.is_active,
        }

        return item

class Genus(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Género")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Género"
        verbose_name_plural = "Géneros"
        ordering = ['name']
        default_permissions = ()
        permissions = (
            ('view_genus_catalog', 'Consultar géneros de plantas'),
            ('add_genus_catalog', 'Crear géneros de plantas'),
            ('change_genus_catalog', 'Editar géneros de plantas'),
            ('delete_genus_catalog', 'Eliminar géneros de plantas'),
        )

    def __str__(self):
        return self.name


class Species(models.Model):
    genus = models.ForeignKey(Genus, on_delete=models.CASCADE, related_name='species', verbose_name="Género")
    name = models.CharField(max_length=100, verbose_name="Especie")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Especie"
        verbose_name_plural = "Especies"
        unique_together = ('genus', 'name')
        ordering = ['name']
        default_permissions = ()
        permissions = (
            ('view_species_catalog', 'Consultar especies de plantas'),
            ('add_species_catalog', 'Crear especies de plantas'),
            ('change_species_catalog', 'Editar especies de plantas'),
            ('delete_species_catalog', 'Eliminar especies de plantas'),
        )

    def __str__(self):
        return f"{self.genus.name} {self.name}"


class Variety(models.Model):
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='varieties', verbose_name="Especie")
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    name = models.CharField(max_length=100, verbose_name="Nombre de Variedad")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Variedad"
        verbose_name_plural = "Variedades"
        ordering = ['name']
        default_permissions = ()
        permissions = (
            ('view_variety_catalog', 'Consultar variedades'),
            ('add_variety_catalog', 'Crear variedades'),
            ('change_variety_catalog', 'Editar variedades'),
            ('delete_variety_catalog', 'Eliminar variedades'),
        )

    def __str__(self):
        return f"{self.name} ({self.code})"


class VarietyTargetGallery(models.Model):
    variety = models.ForeignKey(Variety, on_delete=models.CASCADE, related_name='gallery_targets', verbose_name="Variedad")
    biological_target = models.ForeignKey('BiologicalTarget', on_delete=models.CASCADE, related_name='gallery_varieties', verbose_name="Blanco Biológico")
    image = models.ImageField(upload_to='tenant_galleries/targets/', verbose_name="Imagen de Referencia")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Carga")

    class Meta:
        verbose_name = "Galería de Variedad"
        verbose_name_plural = "Galerías de Variedades"
        unique_together = ('variety', 'biological_target')
        default_permissions = ()
        permissions = (
            ('view_assurance_parameter', 'Consultar parámetros de aseguramiento'),
            ('add_assurance_parameter', 'Crear parámetros de aseguramiento'),
            ('change_assurance_parameter', 'Editar parámetros de aseguramiento'),
            ('delete_assurance_parameter', 'Eliminar parámetros de aseguramiento'),
        )

    def __str__(self):
        return f"Foto: {self.biological_target.name} en {self.variety.name}"

    def save(self, *args, **kwargs):
        """
        Intercepta la imagen para redimensionarla y guardarla en formato .webp,
        optimizando el almacenamiento para el posterior uso Offline-First.
        """
        if self.image and (not self.pk or VarietyTargetGallery.objects.get(pk=self.pk).image != self.image):
            img = Image.open(self.image)
            
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((500, 500), Image.Resampling.LANCZOS)
            
            output = BytesIO()
            img.save(output, format='WEBP', quality=85)
            output.seek(0)
            
            current_name = os.path.splitext(self.image.name)[0]
            self.image = ContentFile(output.read(), name=f"{current_name}.webp")

        super().save(*args, **kwargs)

class AssuranceParameter(models.Model):
    name = models.CharField(max_length=150, verbose_name='Nombre del Parámetro',unique=True)
    description = models.TextField(blank=True, null=True, verbose_name='Descripción / Criterio de Aceptación')
    is_active = models.BooleanField(default=True, verbose_name='Estado Activo')

    class Meta:
        verbose_name = 'Parámetro de Aseguramiento'
        verbose_name_plural = 'Parámetros de Aseguramiento'
        ordering = ['name']
        # Definición explícita de permisos con nombres limpios
        permissions = (
            ('view_assurance_parameter', 'Can view Parámetro de Aseguramiento'),
            ('add_assurance_parameter', 'Can add Parámetro de Aseguramiento'),
            ('change_assurance_parameter', 'Can change Parámetro de Aseguramiento'),
            ('delete_assurance_parameter', 'Can delete Parámetro de Aseguramiento'),
        )

    def __str__(self):
        return self.name

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or '',
            'is_active': self.is_active,
        }