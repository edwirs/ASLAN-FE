import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from core.pos.models import Departamento, Municipio # <--- Cambia "tu_app" por el nombre real de tu app

class Command(BaseCommand):
    help = 'Carga masivamente los departamentos y municipios desde un archivo JSON'

    def handle(self, *args, **kwargs):
        # Ruta donde colocarás tu archivo JSON (por ejemplo, en la raíz del proyecto o dentro de la app)
        json_file_path = os.path.join(settings.BASE_DIR, 'municipios.json')

        if not os.path.exists(json_file_path):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo en: {json_file_path}'))
            return

        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        departamentos_creados = 0
        municipios_creados = 0

        # Recorremos la estructura que mencionaste
        for item in data.get('municipalities', []):
            depto_data = item['department']
            
            # 1. Crear o actualizar el Departamento
            departamento, created_depto = Departamento.objects.get_or_create(
                codigo=depto_data['code'],
                defaults={'nombre': depto_data['name']}
            )
            if created_depto:
                departamentos_creados += 1

            # 2. Crear o actualizar el Municipio relacionado
            _, created_muni = Municipio.objects.get_or_create(
                codigo=item['code'],
                defaults={
                    'nombre': item['name'],
                    'departamento': departamento
                }
            )
            if created_muni:
                municipios_creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Proceso finalizado con éxito. Departamentos nuevos: {departamentos_creados}, Municipios nuevos: {municipios_creados}'
        ))