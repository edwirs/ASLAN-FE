import pandas as pd
from django.db import connection
from core.production.models import PlantInventory


class InventoryImportService:

    @staticmethod
    def process(import_instance):

        try:
            print("🚀 INICIANDO IMPORTACIÓN FULL REPLACE")

            import_instance.status = 'processing'
            import_instance.save()

            # 🔴 1. BORRAR TABLA COMPLETA
            PlantInventory.objects.all().delete()
            print("🗑️ PlantInventory limpiada")

            # 🔴 2. REINICIAR SECUENCIA ID (PostgreSQL)
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER SEQUENCE production_plantinventory_id_seq RESTART WITH 1;"
                )
            print("🔢 Secuencia ID reiniciada")

            # 🔴 3. LEER EXCEL
            df = pd.read_excel(import_instance.file.path)
            df.columns = df.columns.str.strip().str.lower()

            total_records = len(df)
            print(f"📊 TOTAL FILAS EXCEL: {total_records}")

            created_count = 0

            # 🔴 4. INSERT MASIVO
            for index, row in df.iterrows():

                code = row.get('code')

                # validación mínima
                if pd.isna(code):
                    continue

                code = str(code).strip()

                if not code or code.lower() == 'nan':
                    continue

                PlantInventory.objects.create(
                    code=code,
                    plot_id=row.get('plot id'),
                    location=row.get('loca'),
                    agriware_location=row.get('loc agriware'),
                    variety=row.get('variety'),
                    genus=row.get('genus'),
                    species=row.get('species'),
                    breeder=row.get('breeder'),
                    source=row.get('source'),
                    plants=row.get('plants') or 0,
                    area=row.get('area'),
                    planting_date=row.get('planting'),
                    useful_life=row.get('vutil') or 0,
                    maturity=row.get('mad.') or 0,
                    current_age=row.get('hoy') or 0,
                    factor=row.get('fac.') or 0,
                    status=row.get('status'),
                    phytosanitary_status=row.get('fito.'),
                    discard_week=row.get('descarte'),
                    observations=row.get('obs'),
                    is_active=True,
                )

                created_count += 1

                # debug opcional (puedes comentar si es muy lento)
                if index % 500 == 0:
                    print(f"➡️ Procesadas {index} filas...")

            # 🔴 5. FINALIZACIÓN
            import_instance.total_records = total_records
            import_instance.total_created = created_count
            import_instance.total_updated = 0
            import_instance.status = 'completed'
            import_instance.save()

            print("🎯 IMPORTACIÓN COMPLETADA")
            print(f"✔ Insertados: {created_count}")

            return True

        except Exception as e:

            import_instance.status = 'error'
            import_instance.observations = str(e)
            import_instance.save()

            print("💥 ERROR EN IMPORTACIÓN:", str(e))
            raise e