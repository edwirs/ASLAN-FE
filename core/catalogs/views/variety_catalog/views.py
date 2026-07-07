import json
import traceback
import os
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from core.security.mixins import GroupPermissionMixin
from core.catalogs.models import Genus, Species, Variety, BiologicalTarget, VarietyTargetGallery # <-- Importados todos aquí

MODULE_NAME = 'Catálogo de Variedades'

class VarietyCatalogView(GroupPermissionMixin, TemplateView):
    template_name = 'variety_catalog/manage.html'
    permission_required = 'view_variety_catalog'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Administración de Catálogo de Variedades'
        context['module_name'] = MODULE_NAME
        context['list_url'] = reverse_lazy('catalogs:variety_catalog_manage')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        try:
            # --- LECTURAS (READ) ---
            if action == 'list_elements':
                return JsonResponse({
                    'genera': list(Genus.objects.filter(is_active=True).values('id', 'name')),
                    'species': list(Species.objects.filter(is_active=True).values('id', 'name', 'genus_id')),
                    'varieties': list(Variety.objects.filter(is_active=True).values('id', 'name', 'code', 'species_id'))
                })

            # --- GESTIÓN DE GALERÍA (AJAX) ---
            elif action == 'get_variety_gallery':
                variety_id = request.POST.get('variety_id')
                if not variety_id:
                    return JsonResponse({'error': 'Falta el ID de la variedad'}, status=400)
                
                targets = BiologicalTarget.objects.filter(is_active=True)
                gallery_matches = {
                    g.biological_target_id: g.image.url 
                    for g in VarietyTargetGallery.objects.filter(variety_id=variety_id)
                }
                
                data = []
                for t in targets:
                    data.append({
                        'target_id': t.id,
                        'target_name': t.name,
                        'target_code': t.code,
                        'category_name': t.category.name if t.category else 'Sin Categoría',
                        'image_url': gallery_matches.get(t.id, None)
                    })
                
                return JsonResponse({'targets': data})

            elif action == 'save_gallery_image':
                # Validamos contra el permiso personalizado que definiste en la Meta de tu modelo
                if not request.user.has_perm('catalogs.add_target_gallery') and not request.user.has_perm('catalogs.change_target_gallery'):
                    return JsonResponse({'error': 'No tienes permisos para modificar la galería de fotos'}, status=403)
                
                variety_id = request.POST.get('variety_id')
                target_id = request.POST.get('target_id')
                image_file = request.FILES.get('image_file')
                
                if not variety_id or not target_id or not image_file:
                    return JsonResponse({'error': 'Información o archivo de imagen incompleto'}, status=400)
                
                gallery_item, created = VarietyTargetGallery.objects.update_or_create(
                    variety_id=int(variety_id),
                    biological_target_id=int(target_id),
                    defaults={'image': image_file}
                )
                
                return JsonResponse({
                    'success': True, 
                    'message': 'Fotografía actualizada correctamente',
                    'image_url': gallery_item.image.url
                })

            # --- ESCRITURAS DE TAXONOMÍA (CREATE / UPDATE) ---
            elif action == 'save_genus':
                if not request.user.has_perm('catalogs.add_genus_catalog') and not request.user.has_perm('catalogs.change_genus_catalog'):
                    return JsonResponse({'error': 'No tienes permisos para modificar géneros'}, status=403)
                
                genus_id = request.POST.get('id')
                genus_id = int(genus_id) if genus_id and genus_id.isdigit() else None
                name = request.POST.get('name', '').strip()
                
                if not name: 
                    return JsonResponse({'error': 'El nombre del género es obligatorio'})
                
                genus, created = Genus.objects.update_or_create(
                    id=genus_id, 
                    defaults={'name': name, 'is_active': True}
                )
                return JsonResponse({'success': True, 'id': genus.id, 'name': genus.name})

            elif action == 'save_species':
                if not request.user.has_perm('catalogs.add_species_catalog') and not request.user.has_perm('catalogs.change_species_catalog'):
                    return JsonResponse({'error': 'No tienes permisos para modificar especies'}, status=403)
                
                species_id = request.POST.get('id')
                species_id = int(species_id) if species_id and species_id.isdigit() else None
                genus_id = request.POST.get('genus_id')
                name = request.POST.get('name', '').strip()
                
                if not name or not genus_id: 
                    return JsonResponse({'error': 'Datos incompletos: Falta nombre o género base.'})
                
                species, created = Species.objects.update_or_create(
                    id=species_id, 
                    defaults={'name': name, 'genus_id': int(genus_id), 'is_active': True}
                )
                return JsonResponse({'success': True, 'id': species.id, 'name': species.name, 'genus_id': species.genus_id})

            elif action == 'save_variety':
                if not request.user.has_perm('catalogs.add_variety_catalog') and not request.user.has_perm('catalogs.change_variety_catalog'):
                    return JsonResponse({'error': 'No tienes permisos para modificar variedades'}, status=403)
                
                variety_id = request.POST.get('id')
                variety_id = int(variety_id) if variety_id and variety_id.isdigit() else None
                species_id = request.POST.get('species_id')
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                
                if not name or not code or not species_id: 
                    return JsonResponse({'error': 'Datos incompletos para guardar la variedad.'})
                
                variety, created = Variety.objects.update_or_create(
                    id=variety_id, 
                    defaults={'name': name, 'code': code, 'species_id': int(species_id), 'is_active': True}
                )
                return JsonResponse({'success': True, 'id': variety.id, 'name': variety.name, 'code': variety.code, 'species_id': variety.species_id})

            return JsonResponse({'error': f"La acción '{action}' no es válida."})
            
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'error': f"Fallo interno en el servidor: {str(e)}"}, status=500)