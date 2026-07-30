$(function () {
    // Renderiza los cuadros como botones interactivos
    function renderCuadros(naveNum, camaNum) {
        let cuadros = '';
        let totalSections = parseInt($('#id_section_quantity').val());
        
        for (let s = 1; s <= totalSections; s++) {
            let ref = `${naveNum}-${camaNum}-${s}`;
            cuadros += `
                <button type="button" class="btn btn-sm btn-outline-secondary btn-section border rounded" 
                        data-ref="${ref}" 
                        style="flex: 1; font-size: 0.6rem; padding: 2px 0;">
                    ${s}
                </button>`;
        }
        return `<div class="d-flex w-100 gap-1">${cuadros}</div>`;
    }

    function renderNave(naveNumero) {
        let htmlCamas = '';
        let totalCamas = parseInt($('#id_bed_quantity').val());
        let camasPorLado = totalCamas / 2;

        for (let i = 0; i < camasPorLado; i++) {
            let impar = (i * 2) + 1;
            let par = (i * 2) + 2;
            
            htmlCamas += `
                <div class="row g-1 align-items-center mb-1">
                    <div class="col-5">
                        <div class="card border-primary">
                            <div class="card-header py-0 bg-primary text-white text-center" style="font-size: 0.7rem;">Cama ${impar}</div>
                            <div class="card-body p-1">${renderCuadros(naveNumero, impar)}</div>
                        </div>
                    </div>
                    <div class="col-2 text-center p-0"><small class="text-muted" style="font-size: 0.6rem;">PASILLO</small></div>
                    <div class="col-5">
                        <div class="card border-secondary">
                            <div class="card-header py-0 bg-secondary text-white text-center" style="font-size: 0.7rem;">Cama ${par}</div>
                            <div class="card-body p-1">${renderCuadros(naveNumero, par)}</div>
                        </div>
                    </div>
                </div>`;
        }

        return `
            <div class="card shadow-sm border-0 mb-3 nave-box" id="nave_${naveNumero}">
                <div class="card-header py-1 bg-white border-bottom border-primary text-primary text-center">
                    <strong>Nave ${naveNumero}</strong>
                </div>
                <div class="card-body p-2 bg-light">${htmlCamas}</div>
            </div>`;
    }

    $('.btnPreview').on('click', function () {
        let bays = parseInt($('#id_bay_quantity').val());
        let html = `
            <div class="container-fluid text-center my-3">
                <button type="button" class="btn btn-outline-success btn-monitor-all-global">
                    <i class="fas fa-check-double"></i> Monitorear TODOS los cuadros
                </button>
            </div>
            <div class="d-flex flex-wrap">`;
        
        for (let i = 1; i <= bays; i++) {
            html += `<div style="flex: 1 1 350px; padding: 5px;">${renderNave(i)}</div>`;
        }
        
        html += `</div><hr><button type="button" class="btn btn-success btnSaveAll"><i class="fas fa-save"></i> Guardar Bloque Completo</button>`;
        $('#preview').html(html);

        // Si estamos en modo edición, marcamos los cuadros guardados en la BD
        if (typeof IS_EDIT_MODE !== 'undefined' && IS_EDIT_MODE) {
            setTimeout(function() {
                if (typeof INITIAL_MONITORED !== 'undefined') {
                    INITIAL_MONITORED.forEach(function(ref) {
                        let btn = $(`.btn-section[data-ref="${ref}"]`);
                        if (btn.length > 0) {
                            btn.removeClass('btn-outline-secondary').addClass('btn-success');
                        }
                    });
                }
            }, 100);
        }
    });

    $(document).on('click', '.btn-section', function () {
        $(this).toggleClass('btn-outline-secondary btn-success');
    });

    $(document).on('click', '.btn-monitor-all-global', function () {
        $('.btn-section').removeClass('btn-outline-secondary').addClass('btn-success');
        Swal.fire({ icon: 'success', title: 'Seleccionado', text: 'Todos los cuadros marcados', timer: 1000 });
    });

    $(document).on('click', '.btnSaveAll', function () {
        let selected = [];
        $('.btn-section.btn-success').each(function() {
            selected.push($(this).data('ref'));
        });
        
        let postData = {
            'action': 'create',
            'code': $('#id_code').val(),
            'name': $('#id_name').val(),
            'bay_quantity': $('#id_bay_quantity').val(),
            'bed_quantity': $('#id_bed_quantity').val(),
            'section_quantity': $('#id_section_quantity').val(),
            'has_sides': $('#id_has_sides').is(':checked'),
            'selected_sections[]': selected,
            'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
        };

        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            data: postData,
            success: function(response) {
                Swal.fire('Éxito', 'Estructura guardada correctamente', 'success')
                    .then(() => { 
                        window.location.href = BLOCK_LIST_URL; 
                    });
            },
            error: function(xhr) {
                console.error("Error del servidor:", xhr.responseText);
                Swal.fire('Error', 'No se pudo guardar. Revisa los campos obligatorios.', 'error');
            }
        });
    });

    // Carga automática al abrir en modo edición
    if (typeof IS_EDIT_MODE !== 'undefined' && IS_EDIT_MODE) {
        $('.btnPreview').trigger('click');
    }
});