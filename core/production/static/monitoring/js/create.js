var monitoringCapture = {
    inventory: null,
    structure: null,
    targets: [],
    details: [],
    selectedSection: null,
    selectedThird: 'low',
    
    pendingTarget: null,

    sideLabels: { left: 'Izquierdo', right: 'Derecho', both: 'Ambos' },
    thirdLabels: { low: 'Bajo', middle: 'Medio', high: 'Alto' },

    post: function (data, callback) {
        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: data,
            success: callback,
            error: function () {
                Swal.fire({ icon: 'error', title: 'Error', text: 'No fue posible completar la solicitud' });
            }
        });
    },

    fillDatalist: function (selector, items) {
        let html = '';
        items.forEach(function (item) { html += `<option value="${item}"></option>`; });
        $(selector).html(html);
    },

    searchLocations: function () {
        monitoringCapture.post({
            action: 'search_locations',
            code: $('#variety_code').val() 
        }, function (response) {
            monitoringCapture.fillDatalist('#locationOptions', response.items || []);
        });
    },

    searchCodes: function () {
        monitoringCapture.post({
            action: 'search_variety_codes',
            location: $('#location').val()
        }, function (response) {
            monitoringCapture.fillDatalist('#codeOptions', response.items || []);
        });
    },

    loadTargets: function () {
        monitoringCapture.post({ action: 'get_biological_targets' }, function (response) {
            monitoringCapture.targets = response.items || [];
            monitoringCapture.renderTargetsMatrix();
        });
    },

    loadInventory: function () {
        monitoringCapture.post({
            action: 'get_inventory_context',
            location: $('#location').val(),
            code: $('#variety_code').val()
        }, function (response) {
            if (response.error) {
                Swal.fire({ icon: 'warning', title: 'Inventario no encontrado', text: response.error });
                return;
            }

            let sections = response.structure.sections || [];
            if (sections.length === 0) {
                Swal.fire({ icon: 'info', title: 'Sin monitoreo', text: 'Esta ubicación no tiene cuadros configurados.' });
                $('#sectionTabs').html('<p class="text-muted p-2">No hay cuadros configurados.</p>');
                $('#detailPanel').addClass('d-none');
                return;
            }

            monitoringCapture.inventory = response.inventory;
            monitoringCapture.structure = response.structure;
            monitoringCapture.details = [];

            $('#location').val(response.inventory.location);
            $('#variety_code').val(response.inventory.code);

            monitoringCapture.renderInventory(response.inventory);
            monitoringCapture.renderStructure(response.structure, response.monitoring);
            monitoringCapture.renderSections(sections);
            
            monitoringCapture.updateMatrixSelection();
            monitoringCapture.renderDetails();
        });
    },

    renderInventory: function (inventory) {
        $('#summaryVariety').text(inventory.variety || '-');
        $('#summaryPlot').text(inventory.plot_id || '-');
        $('#summaryPlants').text(inventory.plants || '0');
        $('#summaryArea').text(inventory.area || '-');
        $('#inventorySummary').removeClass('d-none');
    },

    renderStructure: function (structure, monitoring) {
        $('#structureBlock').text(structure.block || '-');
        $('#structureBay').text(structure.bay || '-');
        $('#structureBed').text(structure.bed || '-');
        $('#structureSide').text(monitoringCapture.sideLabels[monitoring.bed_side] || '-');
        $('#structureAlert').addClass('d-none');
        $('#detailPanel').removeClass('d-none');
    },

    renderSections: function (sections) {
        let html = '';
        monitoringCapture.selectedSection = sections[0]?.id || null;
        sections.forEach(function (section, index) {
            html += `<button type="button" class="section-tab ${index === 0 ? 'active' : ''}" data-section="${section.id}">Cuadro ${section.number}</button>`;
        });
        $('#sectionTabs').html(html);
    },

    renderTargetsMatrix: function () {
        if (!monitoringCapture.targets.length) return;
        let categories = {};
        monitoringCapture.targets.forEach(function (target) {
            let cat = target.category || 'Otros';
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(target);
        });

        let tabsHtml = '<div class="category-tabs-row">';
        let blocksHtml = '<div class="category-blocks-container">';
        let isFirst = true;
        
        for (let catName in categories) {
            let catClassId = catName.replace(/[^a-zA-Z0-9]/g, '_'); 
            tabsHtml += `<button type="button" class="category-nav-tab ${isFirst ? 'active' : ''}" data-target-cat="${catClassId}">${catName}</button>`;
            blocksHtml += `<div class="matrix-category-block ${isFirst ? 'active' : ''}" id="cat_block_${catClassId}"><div class="matrix-buttons-grid">`;
            categories[catName].forEach(function (target) {
                blocksHtml += `<button type="button" class="target-badge-btn" data-target-id="${target.id}" data-target-name="${target.name}">
                    <i class="far fa-square checkbox-icon"></i> ${target.name}</button>`;
            });
            blocksHtml += `</div></div>`;
            isFirst = false;
        }
        $('#biologicalTargetsMatrix').html(tabsHtml + '</div>' + blocksHtml + '</div>');
    },

    updateMatrixSelection: function () {
        $('.target-badge-btn').removeClass('selected').find('.checkbox-icon').removeClass('fa-check-square fas').addClass('fa-square far');
        if (!monitoringCapture.selectedSection) return;
        monitoringCapture.details.forEach(function (detail) {
            if (String(detail.bed_section_id) === String(monitoringCapture.selectedSection) && detail.third === monitoringCapture.selectedThird) {
                $(`.target-badge-btn[data-target-id="${detail.biological_target_id}"]`).addClass('selected').find('.checkbox-icon').removeClass('fa-square far').addClass('fa-check-square fas');
            }
        });
    },

    toggleTargetSelection: function (btn) {
        if (!monitoringCapture.selectedSection) return;
        let targetId = btn.data('target-id');
        let targetObject = monitoringCapture.targets.find(t => String(t.id) === String(targetId));
        
        let index = monitoringCapture.details.findIndex(d => 
            String(d.bed_section_id) === String(monitoringCapture.selectedSection) && 
            d.third === monitoringCapture.selectedThird && 
            String(d.biological_target_id) === String(targetId)
        );

        if (index > -1) {
            monitoringCapture.details.splice(index, 1);
        } else {
            if (targetObject.severity_grades && targetObject.severity_grades.length > 0) {
                monitoringCapture.pendingTarget = targetObject;
                monitoringCapture.openSeverityModal(targetObject.severity_grades);
                return;
            }
            monitoringCapture.details.push({
                uid: Date.now() + Math.random(),
                bed_section_id: monitoringCapture.selectedSection,
                section_label: $('.section-tab.active').text().trim(),
                third: monitoringCapture.selectedThird,
                third_label: monitoringCapture.thirdLabels[monitoringCapture.selectedThird],
                biological_target_id: targetId,
                biological_target_name: targetObject.name
            });
        }
        monitoringCapture.updateMatrixSelection();
        monitoringCapture.renderDetails();
    },

    openSeverityModal: function (grades) {
        let html = '';
        grades.forEach(g => html += `<button type="button" class="btn btn-outline-dark severity-select-btn" data-grade-id="${g.id}" data-grade-desc="${g.description}">${g.description}</button>`);
        $('#severityOptionsContainer').html(html);
        $('#severityModal').modal('show');
    },

    selectSeverityGrade: function (gradeId, gradeDesc) {
        monitoringCapture.details.push({
            uid: Date.now() + Math.random(),
            bed_section_id: monitoringCapture.selectedSection,
            section_label: $('.section-tab.active').text().trim(),
            third: monitoringCapture.selectedThird,
            third_label: monitoringCapture.thirdLabels[monitoringCapture.selectedThird],
            biological_target_id: monitoringCapture.pendingTarget.id,
            biological_target_name: monitoringCapture.pendingTarget.name,
            severity_grade_id: gradeId,
            severity_grade_description: gradeDesc
        });
        $('#severityModal').modal('hide');
        monitoringCapture.updateMatrixSelection();
        monitoringCapture.renderDetails();
    },

    renderDetails: function () {
        let html = '';
        monitoringCapture.details.forEach(d => {
            html += `<div class="detail-row-pill">${d.section_label} (${d.third_label}) | ${d.biological_target_name} ${d.severity_grade_description ? ' - ' + d.severity_grade_description : ''}
                     <button class="btn-remove-pill btnRemoveDetail" data-uid="${d.uid}"><i class="fas fa-times"></i></button></div>`;
        });
        $('#detailList').html(html || '<div class="text-muted">Ningún hallazgo.</div>');
    },

    save: function () {
        if (!monitoringCapture.inventory) return;
        
        let missingTracks = [];
        monitoringCapture.structure.sections.forEach(s => {
            ['low', 'middle', 'high'].forEach(t => {
                if (!monitoringCapture.details.some(d => String(d.bed_section_id) === String(s.id) && d.third === t))
                    missingTracks.push({ section: s.number, third: monitoringCapture.thirdLabels[t] });
            });
        });

        if (missingTracks.length > 0) {
            let listHtml = `<div class="missing-tracks-container" style="text-align: left; max-height: 250px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; background: #f8fafc; margin-top: 15px;">
                <ul style="list-style: none; padding: 0; margin: 0;">${missingTracks.map(item => `<li style="display: flex; justify-content: space-between; padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 14px;"><span style="font-weight: 600; color: #4a5568;">Cuadro ${item.section}</span><span style="color: #e53e3e; font-family: monospace;">Tercio ${item.third}</span></li>`).join('')}</ul></div>`;
            Swal.fire({ icon: 'warning', title: 'Monitoreo Incompleto', html: `<p>Faltan secciones por registrar:</p>${listHtml}`, width: '400px' });
            return;
        }

        monitoringCapture.post({ action: 'save_monitoring', payload: JSON.stringify({ 
            location: monitoringCapture.inventory.location, 
            variety_code: monitoringCapture.inventory.code,
            details: monitoringCapture.details }) 
        }, res => { if (res.success) window.location.href = res.redirect; else Swal.fire('Error', res.error, 'error'); });
    },

    bindEvents: function () {
        $('#location').on('keyup change', () => { monitoringCapture.searchCodes(); });
        $('#variety_code').on('keyup change', () => { monitoringCapture.searchLocations(); });
        $('.btnLoadInventory').on('click', monitoringCapture.loadInventory);
        $('.btnSaveMonitoring').on('click', monitoringCapture.save);
        
        $(document).on('click', '.section-tab', function() { 
            $('.section-tab').removeClass('active'); $(this).addClass('active'); 
            monitoringCapture.selectedSection = $(this).data('section'); 
            monitoringCapture.updateMatrixSelection(); 
        });
        
        $(document).on('click', '.third-tab', function() { 
            $('.third-tab').removeClass('active'); $(this).addClass('active'); 
            monitoringCapture.selectedThird = $(this).data('third'); 
            monitoringCapture.updateMatrixSelection(); 
        });

        $(document).on('click', '.target-badge-btn', function() { monitoringCapture.toggleTargetSelection($(this)); });
        $(document).on('click', '.severity-select-btn', function() { monitoringCapture.selectSeverityGrade($(this).data('grade-id'), $(this).data('grade-desc')); });
        $(document).on('click', '.btnRemoveDetail', function() { 
            monitoringCapture.details = monitoringCapture.details.filter(d => d.uid !== $(this).data('uid')); 
            monitoringCapture.renderDetails(); monitoringCapture.updateMatrixSelection(); 
        });
        
        $(document).on('click', '.category-nav-tab', function() {
            $('.category-nav-tab').removeClass('active'); $(this).addClass('active');
            $('.matrix-category-block').removeClass('active');
            $('#cat_block_' + $(this).data('target-cat')).addClass('active');
        });
    },

    init: function () {
        monitoringCapture.bindEvents();
        monitoringCapture.loadTargets();
    }
};
$(() => { monitoringCapture.init(); });