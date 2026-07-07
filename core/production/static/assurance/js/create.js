var assuranceCapture = {
    parameters: [],
    inventory: null,
    sliderInstance: null,

    post: function (data, callback) {
        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: data,
            success: callback,
            error: function () {
                alert('No fue posible completar la solicitud en Aseguramiento');
            }
        });
    },

    fillDatalist: function (selector, items) {
        let html = '';
        items.forEach(function (item) {
            html += `<option value="${item}"></option>`;
        });
        $(selector).html(html);
    },

    searchLocations: function () {
        assuranceCapture.post({
            action: 'search_locations',
            code: $('#variety_code').val(),
            term: $('#location').val()
        }, function (response) {
            assuranceCapture.fillDatalist('#locationOptions', response.items || []);
        });
    },

    searchCodes: function () {
        assuranceCapture.post({
            action: 'search_variety_codes',
            location: $('#location').val(),
            term: $('#variety_code').val()
        }, function (response) {
            assuranceCapture.fillDatalist('#codeOptions', response.items || []);
        });
    },

    loadParameters: function () {
        assuranceCapture.post({ 
            action: 'get_biological_targets' 
        }, function (response) {
            if (response.items) {
                assuranceCapture.parameters = response.items;
                assuranceCapture.renderChecklist();
            }
        });
    },

    renderChecklist: function () {
        const $tbody = $('#tblParameters tbody');
        $tbody.empty();

        if (this.parameters.length === 0) {
            $tbody.append(`<tr><td colspan="3" class="text-center py-4 text-muted font-italic">No hay parámetros de aseguramiento activos configurados.</td></tr>`);
            return;
        }

        this.parameters.forEach(param => {
            const row = `
                <tr class="param-row" data-id="${param.id}">
                    <td class="ps-3 py-3">
                        <strong class="d-block text-dark" style="font-size: 14px;">${param.name}</strong>
                        <span class="text-muted d-block unique-msg" style="font-size: 12px;">${param.description || ''}</span>
                    </td>
                    <td class="py-3 text-center">
                        <div class="btn-group btn-check-group" role="group">
                            <input type="radio" class="btn-check" name="complies_${param.id}" id="ok_${param.id}" value="true" checked autocomplete="off">
                            <label class="btn btn-outline-success" for="ok_${param.id}"><i class="fas fa-check"></i> CUMPLE</label>

                            <input type="radio" class="btn-check" name="complies_${param.id}" id="fail_${param.id}" value="false" autocomplete="off">
                            <label class="btn btn-outline-danger" for="fail_${param.id}"><i class="fas fa-xmark"></i> NO CUMPLE</label>
                        </div>
                    </td>
                    <td class="pe-3 py-3">
                        <input type="text" class="txt-observations txt-observations-pretty form-control" placeholder="Añada comentarios u observaciones especiales...">
                    </td>
                </tr>
            `;
            $tbody.append(row);
        });
    },

    buildZoneHtml: function(targets) {
        if (!targets || targets.length === 0) {
            return `<span class="badge-clean"><i class="fas fa-star"></i> Limpio</span>`;
        }
        let html = '';
        targets.forEach(t => {
            html += `
                <div class="fito-pill-group">
                    <span class="badge-fito">${t.name}</span>
                    ${t.severity ? `<span class="badge-severity-view">${t.severity}</span>` : ''}
                </div>
            `;
        });
        return html;
    },

    initDragScroll: function () {
        const slider = document.querySelector('.bed-horizontal-scroll');
        if (!slider) return;
        const newSlider = slider.cloneNode(true);
        slider.parentNode.replaceChild(newSlider, slider);

        let isDown = false, startX, scrollLeft;
        newSlider.addEventListener('mousedown', (e) => {
            isDown = true;
            newSlider.classList.add('active');
            startX = e.pageX - newSlider.offsetLeft;
            scrollLeft = newSlider.scrollLeft;
        });
        newSlider.addEventListener('mouseleave', () => { isDown = false; newSlider.classList.remove('active'); });
        newSlider.addEventListener('mouseup', () => { isDown = false; newSlider.classList.remove('active'); });
        newSlider.addEventListener('mousemove', (e) => {
            if(!isDown) return;
            e.preventDefault();
            const x = e.pageX - newSlider.offsetLeft;
            const walk = (x - startX) * 2.5;
            newSlider.scrollLeft = scrollLeft - walk;
        });
    },

    loadInventoryContext: function () {
        const location = $('#location').val().trim();
        const code = $('#variety_code').val().trim();

        if (!location && !code) {
            alert('Por favor ingrese una localización o un código de variedad.');
            return;
        }

        $('#loadSpinner').removeClass('d-none');
        $('#loadBtnText').addClass('d-none');

        assuranceCapture.post({
            action: 'get_inventory_context',
            location: location,
            code: code
        }, function (response) {
            $('#loadSpinner').addClass('d-none');
            $('#loadBtnText').removeClass('d-none');

            if (response.error) {
                alert(response.error);
                assuranceCapture.resetUI();
            } else {
                assuranceCapture.inventory = response.inventory;
                $('#inventory_id').val(assuranceCapture.inventory.id);
                $('#summaryVariety').text(`${assuranceCapture.inventory.code} - ${assuranceCapture.inventory.variety}`);
                $('#summaryPlot').text(assuranceCapture.inventory.plot_id);
                $('#summaryPlants').text(assuranceCapture.inventory.plants);
                $('#summaryStructure').text(`B: ${response.structure.block} / N: ${response.structure.bay} / C: ${response.structure.bed}`);

                const $matrixRow = $('#matrixContainerRow');
                $matrixRow.empty();

                if (response.matrix_data && response.matrix_data.length > 0) {
                    response.matrix_data.forEach(function (section) {
                        const highHtml = assuranceCapture.buildZoneHtml(section.high);
                        const middleHtml = assuranceCapture.buildZoneHtml(section.middle);
                        const lowHtml = assuranceCapture.buildZoneHtml(section.low);

                        $matrixRow.append(`
                            <div class="section-column-card">
                                <div class="section-column-header">Cuadro ${section.number}</div>
                                <div class="thirds-stack">
                                    <div class="third-cell high-zone"><div class="target-pills-container">${highHtml}</div><span class="zone-tag">Alto</span></div>
                                    <div class="third-cell middle-zone"><div class="target-pills-container">${middleHtml}</div><span class="zone-tag">Medio</span></div>
                                    <div class="third-cell low-zone"><div class="target-pills-container">${lowHtml}</div><span class="zone-tag">Bajo</span></div>
                                </div>
                            </div>
                        `);
                    });
                    $('#mappingContainer').removeClass('d-none');
                    setTimeout(assuranceCapture.initDragScroll, 50);
                } else {
                    $('#mappingContainer').addClass('d-none');
                }

                $('#inventorySummary').removeClass('d-none');
                $('#detailPanel').removeClass('d-none');
            }
        });
    },

    bindEvents: function () {
        $('#location').on('keyup change focus', function () { 
            clearTimeout(window.locTimer); 
            window.locTimer = setTimeout(assuranceCapture.searchCodes, 200); 
            assuranceCapture.searchLocations(); 
        });
        $('#variety_code').on('keyup change focus', function () { 
            clearTimeout(window.codeTimer); 
            window.codeTimer = setTimeout(assuranceCapture.searchLocations, 200); 
            assuranceCapture.searchCodes(); 
        });
        $(document).on('click', '#btnLoadContext, .btnLoadInventory', function (e) {
            e.preventDefault();
            assuranceCapture.loadInventoryContext();
        });
        $('#frmAssurance').on('submit', function (e) {
            e.preventDefault();
            if (!assuranceCapture.inventory) return alert('Debe cargar una localización válida.');
            const details = $('.param-row').map(function () {
                const id = $(this).data('id');
                return { 'parameter_id': id, 'complies': $(this).find(`input[name="complies_${id}"]:checked`).val() === 'true', 'observations': $(this).find('.txt-observations').val().trim() };
            }).get();
            assuranceCapture.post({ action: 'save_assurance', inventory_id: $('#inventory_id').val(), details: JSON.stringify(details) }, function (response) {
                if (response.success) window.location.href = response.redirect_url;
                else alert(response.error || 'Error al guardar.');
            });
        });
    },

    resetUI: function () {
        this.inventory = null;
        $('#inventory_id').val('');
        $('#inventorySummary').addClass('d-none');
        $('#detailPanel').addClass('d-none');
        $('#mappingContainer').addClass('d-none');
    },

    init: function () {
        this.bindEvents();
        this.loadParameters();
        
        // --- NUEVA LÓGICA DE EDICIÓN ---
        if (typeof ASSURANCE_DATA !== 'undefined' && ASSURANCE_DATA !== null) {
            this.loadEditData(ASSURANCE_DATA);
        }
        // -------------------------------
        
        this.searchLocations();
        this.searchCodes();
    },
    loadEditData: function(data) {
        // 1. Rellenar campos básicos
        $('#location').val(data.location).prop('readonly', true);
        $('#variety_code').val(data.variety_code).prop('readonly', true);
        
        // 2. Disparar carga de inventario
        this.loadInventoryContext();

        // 3. Esperar a que se renderice el checklist (retraso breve)
        setTimeout(() => {
            data.details.forEach(detail => {
                const row = $(`.param-row[data-id="${detail.parameter_id}"]`);
                if (row.length) {
                    // Seleccionar radio button
                    row.find(`input[value="${detail.complies}"]`).prop('checked', true);
                    // Rellenar observaciones
                    row.find('.txt-observations').val(detail.observations);
                }
            });
        }, 500);
    }
};

$(function () { assuranceCapture.init(); });