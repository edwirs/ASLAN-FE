var monitoringCapture = {
    inventory: null,
    structure: null,
    targets: [],
    details: [],
    selectedSection: null,
    selectedThird: 'low',
    
    // Variables temporales para gestionar la asignación del modal
    pendingTarget: null,
    pendingBtn: null,

    sideLabels: {
        left: 'Izquierdo',
        right: 'Derecho',
        both: 'Ambos'
    },

    thirdLabels: {
        low: 'Bajo',
        middle: 'Medio',
        high: 'Alto'
    },

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
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'No fue posible completar la solicitud'
                });
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
        monitoringCapture.post({
            action: 'search_locations',
            code: $('#variety_code').val(),
            term: $('#location').val()
        }, function (response) {
            monitoringCapture.fillDatalist('#locationOptions', response.items || []);
        });
    },

    searchCodes: function () {
        monitoringCapture.post({
            action: 'search_variety_codes',
            location: $('#location').val(),
            term: $('#variety_code').val()
        }, function (response) {
            monitoringCapture.fillDatalist('#codeOptions', response.items || []);
        });
    },

    // CAMBIO: Ahora realiza la petición de forma global sin amarrarse a una variedad
    loadTargets: function () {
        let payload = { action: 'get_biological_targets' };

        monitoringCapture.post(payload, function (response) {
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
                Swal.fire({
                    icon: 'warning',
                    title: 'Inventario no encontrado',
                    text: response.error
                });
                return;
            }

            monitoringCapture.inventory = response.inventory;
            monitoringCapture.structure = response.structure;
            monitoringCapture.details = [];

            $('#location').val(response.inventory.location);
            $('#variety_code').val(response.inventory.code);

            monitoringCapture.renderInventory(response.inventory);
            monitoringCapture.renderStructure(response.structure, response.monitoring);
            monitoringCapture.renderSections(response.structure.sections || []);
            
            // CAMBIO: Ya no se sobreescriben ni limpian los blancos fitosanitarios aquí
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

        if (structure.error) {
            $('#structureAlert').removeClass('d-none').text(structure.error);
            $('#detailPanel').addClass('d-none');
            return;
        }

        $('#structureAlert').addClass('d-none').text('');
        $('#detailPanel').removeClass('d-none');
    },

    renderSections: function (sections) {
        let html = '';
        monitoringCapture.selectedSection = null;

        sections.forEach(function (section, index) {
            if (index === 0) {
                monitoringCapture.selectedSection = section.id;
            }

            html += `
                <button
                    type="button"
                    class="section-tab ${index === 0 ? 'active' : ''}"
                    data-section="${section.id}">
                    Cuadro ${section.number}
                </button>
            `;
        });

        $('#sectionTabs').html(html);
    },

    renderTargetsMatrix: function () {
        if (!monitoringCapture.targets.length) return;

        let categories = {};
        monitoringCapture.targets.forEach(function (target) {
            let cat = target.category || 'Otros';
            if (!categories[cat]) {
                categories[cat] = [];
            }
            categories[cat].push(target);
        });

        let tabsHtml = '<div class="category-tabs-row">';
        let blocksHtml = '<div class="category-blocks-container">';
        
        let isFirst = true;
        for (let catName in categories) {
            let catClassId = catName.replace(/[^a-zA-Z0-9]/g, '_'); 
            
            tabsHtml += `
                <button type="button" 
                        class="category-nav-tab ${isFirst ? 'active' : ''}" 
                        data-target-cat="${catClassId}">
                    ${catName}
                </button>
            `;

            blocksHtml += `
                <div class="matrix-category-block ${isFirst ? 'active' : ''}" id="cat_block_${catClassId}">
                    <div class="matrix-buttons-grid">
            `;

            categories[catName].forEach(function (target) {
                let isCleanToken = target.name.toLowerCase().includes('limpio');
                
                let cameraIconHtml = target.has_photos 
                    ? `<span class="btn-view-reference-photo ms-2" data-target-id="${target.id}" data-target-name="${target.name}" title="Ver imágenes de referencia fitosanitaria">
                        <i class="fas fa-camera text-dark"></i>
                       </span>`
                    : '';

                blocksHtml += `
                    <button type="button" 
                            class="target-badge-btn ${isCleanToken ? 'btn-clean-target' : ''}" 
                            data-target-id="${target.id}"
                            data-target-name="${target.name}">
                        <div class="d-flex justify-content-between align-items-center w-100">
                            <div>
                                <i class="far fa-square checkbox-icon"></i> ${isCleanToken ? '✨ ' : ''}${target.name}
                            </div>
                            ${cameraIconHtml}
                        </div>
                    </button>
                `;
            });

            blocksHtml += `
                    </div>
                </div>
            `;
            isFirst = false;
        }

        tabsHtml += '</div>';
        blocksHtml += '</div>';

        $('#biologicalTargetsMatrix').html(tabsHtml + blocksHtml);
        monitoringCapture.updateMatrixSelection();
    },

    updateMatrixSelection: function () {
        $('.target-badge-btn').removeClass('selected')
            .find('.checkbox-icon').removeClass('fa-check-square fas').addClass('fa-square far');

        if (!monitoringCapture.selectedSection || !monitoringCapture.selectedThird) return;

        monitoringCapture.details.forEach(function (detail) {
            if (String(detail.bed_section_id) === String(monitoringCapture.selectedSection) && 
                detail.third === monitoringCapture.selectedThird) {
                
                let btn = $(`.target-badge-btn[data-target-id="${detail.biological_target_id}"]`);
                btn.addClass('selected');
                btn.find('.checkbox-icon').removeClass('fa-square far').addClass('fa-check-square fas');
            }
        });
    },

    toggleTargetSelection: function (btn) {
        if (!monitoringCapture.selectedSection) {
            Swal.fire({ icon: 'warning', title: 'Seleccione un cuadro' });
            return;
        }

        let targetId = btn.data('target-id');
        let targetObject = monitoringCapture.targets.find(t => String(t.id) === String(targetId));
        if (!targetObject) return;

        let targetName = targetObject.name;
        let isCleanToken = targetName.toLowerCase().includes('limpio');

        if (isCleanToken) {
            monitoringCapture.details = monitoringCapture.details.filter(function (detail) {
                return !(String(detail.bed_section_id) === String(monitoringCapture.selectedSection) &&
                         detail.third === monitoringCapture.selectedThird);
            });

            let detail = {
                uid: Date.now() + '-' + Math.random(),
                bed_section_id: monitoringCapture.selectedSection,
                section_label: $('.section-tab.active').text().trim(),
                third: monitoringCapture.selectedThird,
                third_label: monitoringCapture.thirdLabels[monitoringCapture.selectedThird],
                biological_target_id: targetId,
                biological_target_name: targetName,
                is_clean: true,
                severity_grade_id: null,
                severity_grade_description: null
            };
            monitoringCapture.details.push(detail);
            monitoringCapture.updateMatrixSelection();
            monitoringCapture.renderDetails();
        } else {
            monitoringCapture.details = monitoringCapture.details.filter(function (detail) {
                return !(String(detail.bed_section_id) === String(monitoringCapture.selectedSection) &&
                         detail.third === monitoringCapture.selectedThird &&
                         detail.is_clean === true);
            });

            let index = monitoringCapture.details.findIndex(function (detail) {
                return String(detail.bed_section_id) === String(monitoringCapture.selectedSection) &&
                       detail.third === monitoringCapture.selectedThird &&
                       String(detail.biological_target_id) === String(targetId);
            });

            if (index > -1) {
                monitoringCapture.details.splice(index, 1);
                monitoringCapture.updateMatrixSelection();
                monitoringCapture.renderDetails();
            } else {
                if (monitoringCapture.selectedThird === 'high' && targetObject.severity_grades && targetObject.severity_grades.length > 0) {
                    let highestGrade = targetObject.severity_grades[targetObject.severity_grades.length - 1];

                    let detail = {
                        uid: Date.now() + '-' + Math.random(),
                        bed_section_id: monitoringCapture.selectedSection,
                        section_label: $('.section-tab.active').text().trim(),
                        third: monitoringCapture.selectedThird,
                        third_label: monitoringCapture.thirdLabels[monitoringCapture.selectedThird],
                        biological_target_id: targetId,
                        biological_target_name: targetName,
                        is_clean: false,
                        severity_grade_id: highestGrade.id,
                        severity_grade_description: highestGrade.description
                    };
                    monitoringCapture.details.push(detail);
                    monitoringCapture.updateMatrixSelection();
                    monitoringCapture.renderDetails();

                } else if (targetObject.severity_grades && targetObject.severity_grades.length > 0) {
                    monitoringCapture.pendingTarget = targetObject;
                    monitoringCapture.pendingBtn = btn;
                    monitoringCapture.openSeverityModal(targetObject.severity_grades);
                } else {
                    let detail = {
                        uid: Date.now() + '-' + Math.random(),
                        bed_section_id: monitoringCapture.selectedSection,
                        section_label: $('.section-tab.active').text().trim(),
                        third: monitoringCapture.selectedThird,
                        third_label: monitoringCapture.thirdLabels[monitoringCapture.selectedThird],
                        biological_target_id: targetId,
                        biological_target_name: targetName,
                        is_clean: false,
                        severity_grade_id: null,
                        severity_grade_description: null
                    };
                    monitoringCapture.details.push(detail);
                    monitoringCapture.updateMatrixSelection();
                    monitoringCapture.renderDetails();
                }
            }
        }
    },

    openSeverityModal: function (grades) {
        let html = '';
        grades.forEach(function (grade) {
            html += `
                <button type="button" class="btn btn-outline-dark severity-select-btn" 
                        data-grade-id="${grade.id}" 
                        data-grade-desc="${grade.description}">
                    <i class="fas fa-layer-group me-2 text-muted"></i> ${grade.description}
                </button>
            `;
        });
        $('#severityOptionsContainer').html(html);
        $('#severityModal').modal('show');
    },

    selectSeverityGrade: function (gradeId, gradeDesc) {
        if (!monitoringCapture.pendingTarget) return;

        let detail = {
            uid: Date.now() + '-' + Math.random(),
            bed_section_id: monitoringCapture.selectedSection,
            section_label: $('.section-tab.active').text().trim(),
            third: monitoringCapture.selectedThird,
            third_label: monitoringCapture.thirdLabels[monitoringCapture.selectedThird],
            biological_target_id: monitoringCapture.pendingTarget.id,
            biological_target_name: monitoringCapture.pendingTarget.name,
            is_clean: false,
            severity_grade_id: gradeId,
            severity_grade_description: gradeDesc
        };

        monitoringCapture.details.push(detail);
        $('#severityModal').modal('hide');
        
        monitoringCapture.pendingTarget = null;
        monitoringCapture.pendingBtn = null;

        monitoringCapture.updateMatrixSelection();
        monitoringCapture.renderDetails();
    },

    renderDetails: function () {
        let html = '';

        if (!monitoringCapture.details.length) {
            $('#detailList').html(`
                <div class="structure-alert text-muted background-none" style="background:transparent; border:none; padding:0;">
                    Ningún blanco biológico seleccionado en esta cama.
                </div>
            `);
            return;
        }

        monitoringCapture.details.forEach(function (detail) {
            let colorBadge = detail.is_clean ? 'bg-info' : 'bg-danger';
            let gradeBadge = detail.severity_grade_description 
                ? `<span class="badge bg-dark text-wrap" style="max-width: 140px;">${detail.severity_grade_description}</span>` 
                : '';

            html += `
                <div class="detail-row-pill">
                    <span class="badge bg-success">${detail.section_label}</span>
                    <span class="badge bg-secondary">${detail.third_label}</span>
                    <span class="badge ${colorBadge}">${detail.is_clean ? 'OK' : 'FITO'}</span>
                    ${gradeBadge}
                    <strong class="target-text">${detail.biological_target_name}</strong>
                    <button type="button" class="btn-remove-pill btnRemoveDetail" data-uid="${detail.uid}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });

        $('#detailList').html(html);
    },

    save: function () {
        if (!monitoringCapture.inventory || !monitoringCapture.structure) {
            Swal.fire({ icon: 'warning', title: 'Cargue primero el inventario' });
            return;
        }

        let totalSections = monitoringCapture.structure.sections || [];
        let missingTracks = [];

        totalSections.forEach(function (section) {
            ['low', 'middle', 'high'].forEach(function (thirdCode) {
                let hasRecord = monitoringCapture.details.some(function (detail) {
                    return String(detail.bed_section_id) === String(section.id) && detail.third === thirdCode;
                });

                if (!hasRecord) {
                    let labelThird = monitoringCapture.thirdLabels[thirdCode];
                    missingTracks.push(`Cuadro ${section.number} - Tercio ${labelThird}`);
                }
            });
        });

        if (missingTracks.length > 0) {
            let errorListHtml = '<div style="text-align:left; font-size:14px; max-height:150px; overflow-y:auto; margin-top:10px; border:1px solid #ecc94b; background:#fffdf5; padding:8px; border-radius:6px;"><ul>';
            missingTracks.forEach(function (item) { errorListHtml += `<li style="margin-bottom:4px;">${item}</li>`; });
            errorListHtml += '</ul></div>';

            Swal.fire({
                icon: 'error',
                title: 'Monitoreo Incompleto',
                html: `<p>Para asegurar que recorrió toda la cama, debe registrar al menos un hallazgo (o marcar Limpio) en:</p>${errorListHtml}`,
                confirmButtonText: 'Revisar y Completar'
            });
            return;
        }

        let fitoDetails = monitoringCapture.details.filter(function(d) { return !d.is_clean; });

        let payload = {
            location: monitoringCapture.inventory.location,
            variety_code: monitoringCapture.inventory.code,
            monitored_quantity: 0, 
            details: fitoDetails.map(function (detail) {
                return {
                    bed_section_id: detail.bed_section_id,
                    third: detail.third,
                    biological_target_id: detail.biological_target_id,
                    affected_quantity: 0,
                    severity: 0,
                    severity_grade_id: detail.severity_grade_id,
                    observations: ''
                };
            })
        };

        monitoringCapture.post({
            action: 'save_monitoring',
            payload: JSON.stringify(payload)
        }, function (response) {
            if (response.error) {
                Swal.fire({ icon: 'error', title: 'No se pudo guardar', text: response.error });
                return;
            }

            Swal.fire({ icon: 'success', title: 'Monitoreo guardado exitosamente' }).then(function () {
                window.location.href = response.redirect;
            });
        });
    },

    bindEvents: function () {
        let locationTimer = null;
        let codeTimer = null;

        $('#location').on('keyup change', function () {
            clearTimeout(locationTimer);
            locationTimer = setTimeout(monitoringCapture.searchCodes, 250);
            monitoringCapture.searchLocations();
        });

        $('#variety_code').on('keyup change', function () {
            clearTimeout(codeTimer);
            codeTimer = setTimeout(monitoringCapture.searchLocations, 250);
            monitoringCapture.searchCodes();
        });

        $('.btnLoadInventory').on('click', monitoringCapture.loadInventory);
        $('.btnSaveMonitoring').on('click', monitoringCapture.save);

        $(document).on('click', '.section-tab', function () {
            $('.section-tab').removeClass('active');
            $(this).addClass('active');
            monitoringCapture.selectedSection = $(this).data('section');
            monitoringCapture.updateMatrixSelection();
        });

        $(document).on('click', '.third-tab', function () {
            $('.third-tab').removeClass('active');
            $(this).addClass('active');
            monitoringCapture.selectedThird = $(this).data('third');
            monitoringCapture.updateMatrixSelection();
        });

        $(document).on('click', '.category-nav-tab', function () {
            $('.category-nav-tab').removeClass('active');
            $(this).addClass('active');
            
            let targetCat = $(this).data('target-cat');
            $('.matrix-category-block').removeClass('active');
            $(`#cat_block_${targetCat}`).addClass('active');
        });

        $(document).on('click', '.target-badge-btn', function (e) {
            if ($(e.target).closest('.btn-view-reference-photo').length) return;
            monitoringCapture.toggleTargetSelection($(this));
        });

        $(document).on('click', '.severity-select-btn', function () {
            let gradeId = $(this).data('grade-id');
            let gradeDesc = $(this).data('grade-desc');
            monitoringCapture.selectSeverityGrade(gradeId, gradeDesc);
        });

        $(document).on('click', '.btnRemoveDetail', function () {
            let uid = $(this).data('uid');
            monitoringCapture.details = monitoringCapture.details.filter(function (detail) { return detail.uid !== uid; });
            monitoringCapture.renderDetails();
            monitoringCapture.updateMatrixSelection();
        });

        // =============================================================
        // EVENTO MODIFICADO: RENDERIZA TODAS LAS FOTOS DEL REPOSITORIO
        // =============================================================
        $(document).on('click', '.btn-view-reference-photo', function (e) {
            e.stopPropagation(); 
            
            let targetId = $(this).data('target-id');
            let targetName = $(this).data('target-name');
            
            $('#referencePhotosTitle').html(`<i class="fas fa-images me-2"></i>Referencias: <b>${targetName}</b>`);

            // Consumimos el nuevo endpoint enviando el id del hongo/insecto únicamente
            monitoringCapture.post({
                action: 'get_target_gallery',
                target_id: targetId
            }, function (response) {
                if (response.error) {
                    Swal.fire('Error', response.error, 'error');
                    return;
                }

                let html = '';

                // Recorremos todas las fotos asociadas a ese blanco biológico
                if (response.photos && response.photos.length > 0) {
                    response.photos.forEach(function (photo) {
                        html += `
                            <div class="col-12 mb-3">
                                <div class="ref-photo-card" style="border: 1px solid #ddd; border-radius: 6px; overflow: hidden;">
                                    <img src="${photo.image_url}" class="ref-photo-img" style="width:100%; height:250px; object-fit:cover;">
                                    <div class="p-2 bg-light text-center border-top">
                                        <small class="text-muted font-weight-bold">Variedad: ${photo.variety_name}</small>
                                    </div>
                                </div>
                            </div>`;
                    });
                } else {
                    html = `<div class="col-12 text-center text-muted py-4"><p>No se encontraron las imágenes en el repositorio.</p></div>`;
                }

                $('#reference-photos-container').html(html);
                
                let refModal = new bootstrap.Modal(document.getElementById('viewReferencePhotosModal'));
                refModal.show();
            });
        });
    },

    init: function () {
        monitoringCapture.bindEvents();
        monitoringCapture.loadTargets(); // Carga inicial global
        monitoringCapture.searchLocations();
        monitoringCapture.searchCodes();
    }
};

$(function () {
    monitoringCapture.init();
});