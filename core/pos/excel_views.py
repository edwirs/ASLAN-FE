"""Vistas base de exportar / plantilla / importar Excel; cada módulo indica su permiso y sus funciones."""
from datetime import date

from django.http import HttpResponse, JsonResponse
from django.views import View

from core.pos.excel_utils import ImportFileError
from core.security.mixins import StrictPermissionMixin

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def xlsx_response(content, filename):
    response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


class ExcelExportView(StrictPermissionMixin, View):
    """Descarga todos los registros en Excel (mismas columnas de la plantilla de importación)."""
    build = None          # función sin argumentos que devuelve los bytes del .xlsx
    file_prefix = ''      # clientes -> clientes_AAAAMMDD.xlsx

    def get(self, request, *args, **kwargs):
        return xlsx_response(type(self).build(), f'{self.file_prefix}_{date.today():%Y%m%d}.xlsx')


class ExcelTemplateView(StrictPermissionMixin, View):
    """Plantilla de Excel para cargar registros de forma masiva."""
    build = None
    file_name = ''

    def get(self, request, *args, **kwargs):
        return xlsx_response(type(self).build(), self.file_name)


class ExcelImportView(StrictPermissionMixin, View):
    """Crea los registros de un archivo de Excel (.xlsx o .xls) y devuelve el resumen fila por fila."""
    run = None            # función (archivo) -> dict con total, created, skipped, errors

    def post(self, request, *args, **kwargs):
        uploaded = request.FILES.get('file')
        if uploaded is None:
            return JsonResponse({'error': 'Seleccione el archivo de Excel a importar.'})
        try:
            return JsonResponse(type(self).run(uploaded))
        except ImportFileError as e:
            return JsonResponse({'error': str(e)})
        except Exception:
            return JsonResponse({'error': 'No se pudo importar el archivo. Verifique que use la plantilla.'})
