import os
from datetime import datetime

from django.db import models
from django.db.models import Sum, FloatField
from django.db.models.functions import Coalesce
from django.forms import model_to_dict
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from django.utils import timezone

from core.user.models import User
from core.catalogs.models import BiologicalTarget, Block, BlockBay, Bed, BedSection, SeverityGrade, AssuranceParameter, Block, BlockBay, Bed, BedSection, TrapICA, TrapCopitarsia, TrapIn, TrapOut

from config import settings

class PlantInventory(models.Model):
    # Identificación
    plot_id = models.CharField(max_length=50,blank=True,null=True,db_index=True,verbose_name='Plot ID')
    code = models.CharField(max_length=50,db_index=True,verbose_name='Código')
    # Ubicación
    location = models.CharField(max_length=100,db_index=True,verbose_name='Ubicación')
    agriware_location = models.CharField(max_length=100,blank=True,null=True,verbose_name='Ubicación Agriware')
    # Material vegetal
    variety = models.CharField(max_length=150,db_index=True,verbose_name='Variedad')
    genus = models.CharField(max_length=150,blank=True,null=True,db_index=True,verbose_name='Género')
    species = models.CharField(max_length=150,blank=True,null=True,db_index=True,verbose_name='Especie')
    breeder = models.CharField(max_length=150,blank=True,null=True,db_index=True,verbose_name='Breeder')
    source = models.CharField(max_length=150,blank=True,null=True,db_index=True,verbose_name='Origen')
    # Inventario
    plants = models.PositiveIntegerField(default=0,verbose_name='Cantidad de Plantas')
    area = models.CharField(max_length=100,blank=True,null=True,verbose_name='Área')
    # Fechas
    planting_date = models.DateField(blank=True,null=True,verbose_name='Fecha Siembra')
    # Indicadores agronómicos
    useful_life = models.IntegerField(default=0,verbose_name='Vida Útil (Semanas)')
    maturity = models.IntegerField(default=0,verbose_name='Madurez (Semanas)')
    current_age = models.IntegerField(default=0,verbose_name='Edad Actual (Semanas)')
    factor = models.DecimalField(max_digits=10,decimal_places=2,default=0,verbose_name='Factor')
    # Estado
    status = models.CharField(max_length=100,blank=True,null=True,verbose_name='Estado')
    phytosanitary_status = models.CharField(max_length=255,blank=True,null=True,verbose_name='Estado Fitosanitario')
    discard_week = models.CharField(max_length=50,blank=True,null=True,verbose_name='Semana Descarte')
    observations = models.TextField(blank=True,null=True,verbose_name='Observaciones')
    is_active = models.BooleanField(default=True,verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.plot_id} - {self.variety}'

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Inventario de Plantas'
        verbose_name_plural = 'Inventario de Plantas'

        default_permissions = ()

        permissions = (
            ('view_plant_inventory', 'Consultar Inventario de Plantas'),
            ('add_plant_inventory', 'Crear Inventario de Plantas'),
            ('change_plant_inventory', 'Editar Inventario de Plantas'),
            ('delete_plant_inventory', 'Eliminar Inventario de Plantas'),
            ('import_plant_inventory', 'Importar Inventario de Plantas'),
        )

class PlantInventoryImport(models.Model):
    file = models.FileField(upload_to='inventory_import/%Y/%m/',verbose_name='Archivo')
    imported_at = models.DateTimeField(auto_now_add=True,verbose_name='Fecha de importación')
    imported_by = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Usuario')
    total_records = models.PositiveIntegerField(default=0,verbose_name='Registros procesados')
    total_created = models.PositiveIntegerField(default=0,verbose_name='Registros creados')
    total_updated = models.PositiveIntegerField(default=0,verbose_name='Registros actualizados')
    observations = models.TextField(blank=True,null=True,verbose_name='Observaciones')

    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('error', 'Error'),
    )

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending',verbose_name='Estado')

    def __str__(self):
        return f'Importación #{self.id}'

    def toJSON(self):
        item = model_to_dict(self)
        item['file'] = self.file.name if self.file else ''
        item['imported_at'] = self.imported_at.strftime('%Y-%m-%d %H:%M:%S')
        item['imported_by'] = self.imported_by.username
        item['status'] = self.get_status_display()

        return item

    class Meta:
        verbose_name = 'Importación Inventario Plantas'
        verbose_name_plural = 'Importaciones Inventario Plantas'
        default_permissions = ()
        permissions = (
            ('view_plant_inventory_import', 'Consultar Importaciones de Inventario'),
            ('add_plant_inventory_import', 'Crear Importaciones de Inventario'),
            ('process_plant_inventory_import', 'Procesar Importaciones de Inventario'),
            ('delete_plant_inventory_import', 'Eliminar Importaciones de Inventario'),
        )

class Monitoring(models.Model):
    BED_SIDE_CHOICES = (
        ('left', 'Izquierdo'),
        ('right', 'Derecho'),
        ('both', 'Ambos'),
    )

    monitoring_date = models.DateField(verbose_name='Fecha Monitoreo')
    week = models.PositiveIntegerField(verbose_name='Semana')
    location = models.CharField(max_length=200,verbose_name='Ubicación')
    block = models.ForeignKey(Block,on_delete=models.PROTECT,blank=True,null=True,verbose_name='Bloque')
    bay = models.ForeignKey(BlockBay,on_delete=models.PROTECT,blank=True,null=True,verbose_name='Nave')
    bed = models.ForeignKey(Bed,on_delete=models.PROTECT,blank=True,null=True,verbose_name='Cama')
    bed_side = models.CharField(max_length=10,choices=BED_SIDE_CHOICES,blank=True,null=True,verbose_name='Lado monitoreado')
    variety_code = models.CharField(max_length=50,verbose_name='Código Variedad')
    variety_name = models.CharField(max_length=150,verbose_name='Variedad')
    plot_id = models.CharField(max_length=100,blank=True,null=True,verbose_name='Plot ID')
    monitored_quantity = models.PositiveIntegerField(default=0,verbose_name='Cantidad Monitoreada')
    monitoring_type = models.CharField(max_length=20,choices=(('basket', 'Canastillas'),('bed', 'Camas'),),verbose_name='Tipo Monitoreo')
    monitored_by = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Monitor')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Monitoreo'
        verbose_name_plural = 'Monitoreos'
        ordering = ['-monitoring_date']
        default_permissions = ()
        permissions = (
            ('add_monitoring', 'Crear monitoreos'),
            ('change_monitoring', 'Editar monitoreos'),
            ('delete_monitoring', 'Eliminar monitoreos'),
            ('view_monitoring', 'Consultar monitoreos'),
        )

    def __str__(self):
        return f'{self.location} - {self.variety_code}'

    def toJSON(self):
        item = model_to_dict(self)
        item['monitoring_date'] = (
            self.monitoring_date.strftime('%Y-%m-%d')
            if self.monitoring_date
            else ''
        )
        item['monitored_by'] = (
            str(self.monitored_by)
            if self.monitored_by
            else ''
        )
        item['block'] = str(self.block) if self.block else ''
        item['bay'] = str(self.bay) if self.bay else ''
        item['bed'] = str(self.bed) if self.bed else ''
        item['bed_side_display'] = self.get_bed_side_display() if self.bed_side else ''

        return item

class MonitoringDetail(models.Model):
    THIRD_CHOICES = (
        ('low', 'Bajo'),
        ('middle', 'Medio'),
        ('high', 'Alto'),
    )

    monitoring = models.ForeignKey(Monitoring,on_delete=models.CASCADE,related_name='details')
    bed_section = models.ForeignKey(BedSection,on_delete=models.PROTECT,blank=True,null=True,verbose_name='Cuadro')
    third = models.CharField(max_length=10,choices=THIRD_CHOICES,blank=True,null=True,verbose_name='Tercio')
    biological_target = models.ForeignKey(BiologicalTarget,on_delete=models.PROTECT,verbose_name='Objetivo Biológico')
    affected_quantity = models.PositiveIntegerField(default=0,verbose_name='Cantidad Afectada')
    severity = models.DecimalField(max_digits=5,decimal_places=2,default=0,verbose_name='Severidad (%)')
    severity_grade = models.ForeignKey(SeverityGrade, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Grado de Severidad')
    observations = models.TextField(blank=True,null=True,verbose_name='Observaciones')

    class Meta:

        verbose_name = 'Detalle Monitoreo'
        verbose_name_plural = 'Detalles Monitoreo'
        default_permissions = ()
        permissions = (
            ('add_monitoring_detail', 'Crear detalles monitoreo'),
            ('change_monitoring_detail', 'Editar detalles monitoreo'),
            ('delete_monitoring_detail', 'Eliminar detalles monitoreo'),
            ('view_monitoring_detail', 'Consultar detalles monitoreo'),
        )
        unique_together = (
            ('monitoring', 'bed_section', 'third', 'biological_target'),
        )

    def __str__(self):
        return str(self.biological_target)

    def toJSON(self):
        item = model_to_dict(self)
        item['biological_target'] = str(
            self.biological_target
        )
        item['bed_section'] = str(self.bed_section) if self.bed_section else ''
        item['third_display'] = self.get_third_display() if self.third else ''
        item['severity_grade'] = {
            'id': self.severity_grade.id,
            'name': self.severity_grade.name,
            'grade_number': self.severity_grade.grade_number,
            'description': self.severity_grade.description
        } if self.severity_grade else None

        return item

class MonitoringConfiguration(models.Model):
    BED_SIDE_CHOICES = (
        ('left', 'Izquierdo'),
        ('right', 'Derecho'),
        ('both', 'Ambos'),
    )

    block = models.OneToOneField(Block,on_delete=models.CASCADE)
    monitoring_type = models.CharField(max_length=20,choices=(('basket', 'Canastillas'),('bed', 'Camas'),),default='bed')
    monitoring_rotation = models.CharField(max_length=20,choices=(('side', 'Lado A / Lado B'),('bed', 'Cama Completa'),),default='side')
    even_week_side = models.CharField(max_length=10,choices=BED_SIDE_CHOICES,default='right',verbose_name='Lado semana par')
    odd_week_side = models.CharField(max_length=10,choices=BED_SIDE_CHOICES,default='left',verbose_name='Lado semana impar')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Configuración Monitoreo'
        verbose_name_plural = 'Configuraciones Monitoreo'
        default_permissions = ()
        permissions = (
            ('add_monitoring_configuration','Crear configuraciones monitoreo'),
            ('change_monitoring_configuration','Editar configuraciones monitoreo'),
            ('delete_monitoring_configuration','Eliminar configuraciones monitoreo'),
            ('view_monitoring_configuration','Consultar configuraciones monitoreo'),
        )

    def __str__(self):
        return str(self.block)

class Assurance(models.Model):
    # Tipos de lados de cama
    SIDE_CHOICES = (
        ('left', 'Izquierdo'),
        ('right', 'Derecho'),
        ('both', 'Ambos'),
    )

    assurance_date = models.DateField(verbose_name='Fecha de Aseguramiento')
    week = models.PositiveIntegerField(verbose_name='Número de Semana')
    location = models.CharField(max_length=50, verbose_name='Ubicación (Bloque.Nave.Cama)')
    block = models.ForeignKey(Block, on_delete=models.SET_NULL, null=True, blank=True)
    bay = models.ForeignKey(BlockBay, on_delete=models.SET_NULL, null=True, blank=True)
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True)
    bed_side = models.CharField(max_length=10, choices=SIDE_CHOICES, default='both', verbose_name='Lado de la Cama')
    variety_code = models.CharField(max_length=50, verbose_name='Código de Variedad')
    variety_name = models.CharField(max_length=150, verbose_name='Nombre de Variedad')
    plot_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='ID Lote / Cama Física')
    audited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='Auditado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')

    class Meta:
        verbose_name = 'Aseguramiento en Campo'
        verbose_name_plural = 'Aseguramientos en Campo'
        ordering = ['-assurance_date', '-id']
        default_permissions = ()
        permissions = (
            ('view_assurance', 'Consultar aseguramientos en campo'),
            ('add_assurance', 'Crear aseguramientos en campo'),
            ('change_assurance', 'Editar aseguramientos en campo'),
            ('delete_assurance', 'Eliminar aseguramientos en campo'),
        )

    def __str__(self):
        return f"{self.location} - {self.assurance_date} (Semana {self.week})"

    def toJSON(self):
        item = {
            'id': self.id,
            'date': self.assurance_date.strftime('%Y-%m-%d') if self.assurance_date else '',
            'location': self.location,
            'variety': self.variety_name,
            'auditor': self.audited_by.get_full_name() if self.audited_by and hasattr(self.audited_by, 'get_full_name') else str(self.audited_by),
        }
        return item


class AssuranceDetail(models.Model):
    # Definición de tercios simplificada
    THIRD_CHOICES = (
        ('low', 'Bajo'),
        ('middle', 'Medio'),
        ('high', 'Alto'),
    )

    assurance = models.ForeignKey(Assurance, on_delete=models.CASCADE, related_name='details', verbose_name='Aseguramiento')
    bed_section = models.ForeignKey(BedSection, on_delete=models.SET_NULL, null=True, blank=True)
    third = models.CharField(max_length=10, choices=THIRD_CHOICES, verbose_name='Tercio de la Planta')
    parameter = models.ForeignKey(AssuranceParameter, on_delete=models.PROTECT, verbose_name='Parámetro de Aseguramiento')
    complies = models.BooleanField(default=True, verbose_name='¿Cumple?')
    observations = models.TextField(blank=True, null=True, verbose_name='Observaciones / Hallazgos')

    class Meta:
        verbose_name = 'Detalle de Aseguramiento'
        verbose_name_plural = 'Detalles de Aseguramiento'
        ordering = ['id']
        default_permissions = ()
        permissions = (
            ('view_assurance_detail', 'Consultar detalles de aseguramiento'),
            ('add_assurance_detail', 'Crear detalles de aseguramiento'),
            ('change_assurance_detail', 'Editar detalles de aseguramiento'),
            ('delete_assurance_detail', 'Eliminar detalles de aseguramiento'),
        )

    def __str__(self):
        return f"{self.parameter.name} - {'CUMPLE' if self.complies else 'NO CUMPLE'}"

    def toJSON(self):
        item = model_to_dict(self)
        item['parameter'] = str(self.parameter) if self.parameter else 'N/A'
        item['bed_section'] = str(self.bed_section) if self.bed_section else 'N/A'
        # get_third_display es un método automático de Django para campos con 'choices'
        item['third_display'] = self.get_third_display() if self.third else ''
        return item

class ReadingICA(models.Model):
    trap = models.ForeignKey(TrapICA, on_delete=models.CASCADE, verbose_name="Trampa ICA")
    date_reading = models.DateField(default=datetime.now, verbose_name="Fecha de lectura")
    quantity = models.IntegerField(default=0, verbose_name="Cantidad")
    observation = models.TextField(blank=True, null=True, verbose_name="Observación")

    class Meta:
        verbose_name = "Registro ICA"
        verbose_name_plural = "Registros ICA"
        ordering = ['-date_reading']
        default_permissions = ()
        permissions = (
            ('view_reading_ica', 'Consultar registros ICA'),
            ('add_reading_ica', 'Crear registros ICA'),
            ('change_reading_ica', 'Editar registros ICA'),
            ('delete_reading_ica', 'Eliminar registros ICA'),
        )

    def __str__(self):
        return f"{self.trap.name} - {self.date_reading}"

    def toJSON(self):
        item = model_to_dict(self)
        item['trap'] = self.trap.toJSON()
        item['date_reading'] = self.date_reading.strftime('%Y-%m-%d')
        return item

class ReadingCopitarsia(models.Model):
    trap = models.ForeignKey(TrapCopitarsia, on_delete=models.CASCADE, verbose_name="Trampa Copitarsia")
    date_reading = models.DateField(default=datetime.now, verbose_name="Fecha de lectura")
    quantity = models.IntegerField(default=0, verbose_name="Cantidad")
    observation = models.TextField(blank=True, null=True, verbose_name="Observación")

    class Meta:
        verbose_name = "Registro Copitarsia"
        verbose_name_plural = "Registros Copitarsia"
        ordering = ['-date_reading']
        default_permissions = ()
        permissions = (
            ('view_reading_copitarsia', 'Consultar registros Copitarsia'),
            ('add_reading_copitarsia', 'Crear registros Copitarsia'),
            ('change_reading_copitarsia', 'Editar registros Copitarsia'),
            ('delete_reading_copitarsia', 'Eliminar registros Copitarsia'),
        )

    def __str__(self):
        return f"{self.trap.name} - {self.date_reading}"

    def toJSON(self):
        item = model_to_dict(self)
        item['trap'] = self.trap.toJSON()
        item['date_reading'] = self.date_reading.strftime('%Y-%m-%d')
        return item

class ReadingInternalTrap(models.Model):
    trap_in = models.ForeignKey(TrapIn, on_delete=models.PROTECT, verbose_name="Trampa Interna")
    date_reading = models.DateField(verbose_name="Fecha de lectura")
    observation = models.TextField(blank=True, null=True, verbose_name="Observación")

    class Meta:
        verbose_name = "Lectura Trampa Interna"
        verbose_name_plural = "Lecturas Trampas Internas"
        default_permissions = ()
        permissions = (
            ('view_reading_internal_trap', 'Consultar lecturas trampas internas'),
            ('add_reading_internal_trap', 'Crear lecturas trampas internas'),
        )

    def __str__(self):
        return f"{self.trap_in.name} - {self.date_reading}"

    def toJSON(self):
        item = model_to_dict(self)
        item['trap_in'] = self.trap_in.toJSON()
        item['date_reading'] = self.date_reading.strftime('%Y-%m-%d')
        item['block'] = self.trap_in.block.toJSON() 
        item['name'] = self.trap_in.name
        return item

class ReadingInternalTrapDetail(models.Model):
    reading = models.ForeignKey(ReadingInternalTrap, on_delete=models.CASCADE, related_name='details')
    biological_target = models.ForeignKey(BiologicalTarget, on_delete=models.PROTECT, verbose_name="Blanco Biológico")
    quantity = models.IntegerField(default=0, verbose_name="Cantidad")

    class Meta:
        verbose_name = "Detalle de Lectura"
        verbose_name_plural = "Detalles de Lecturas"
        default_permissions = ()

    def toJSON(self):
        item = model_to_dict(self)
        item['biological_target'] = self.biological_target.toJSON()
        return item

class ReadingExternalTrap(models.Model):
    trap_out = models.ForeignKey(TrapOut, on_delete=models.PROTECT, verbose_name="Trampa Externa")
    date_reading = models.DateField(verbose_name="Fecha de lectura")
    observation = models.TextField(blank=True, null=True, verbose_name="Observación")

    class Meta:
        verbose_name = "Lectura Trampa Externa"
        verbose_name_plural = "Lecturas Trampas Externas"
        default_permissions = ()
        permissions = (
            ('view_reading_external_trap', 'Consultar lecturas trampas externas'),
            ('add_reading_external_trap', 'Crear lecturas trampas externas'),
        )

    def __str__(self):
        return f"{self.trap_in.name} - {self.date_reading}"

    def toJSON(self):
        item = model_to_dict(self)
        item['trap_out'] = self.trap_out.toJSON()
        item['date_reading'] = self.date_reading.strftime('%Y-%m-%d')
        item['name'] = self.trap_out.name
        return item

class ReadingExternalTrapDetail(models.Model):
    reading = models.ForeignKey(ReadingExternalTrap, on_delete=models.CASCADE, related_name='details')
    biological_target = models.ForeignKey(BiologicalTarget, on_delete=models.PROTECT, verbose_name="Blanco Biológico")
    quantity = models.IntegerField(default=0, verbose_name="Cantidad")

    class Meta:
        verbose_name = "Detalle de Lectura"
        verbose_name_plural = "Detalles de Lecturas"
        default_permissions = ()

    def toJSON(self):
        item = model_to_dict(self)
        item['biological_target'] = self.biological_target.toJSON()
        return item