// Configuraciones adicionales (Clientes, Productos...): abrir la importación de Excel, validar el archivo y mostrar el
// resultado. Usa el HTML de templates/partials/excel_tools_panel.html.
$(function () {
    var MAX_SIZE = 5 * 1024 * 1024;
    var modalEl = document.getElementById('modalExcelImport');
    if (!modalEl) {
        return;   // sin permiso para crear registros la importación no se dibuja
    }
    var modal = new bootstrap.Modal(modalEl);
    var offcanvasEl = document.getElementById('offcanvasExcelTools');
    var input = document.getElementById('importFile');
    var button = document.getElementById('btnImportRun');
    var error = document.getElementById('importFileError');
    var result = document.getElementById('importResult');
    var buttonHtml = button.innerHTML;
    var entity = modalEl.dataset.entity || 'registros';

    function escapeHtml(text) {
        return String(text).replace(/[&<>"']/g, function (c) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
        });
    }

    function reset() {
        input.value = '';
        error.hidden = true;
        result.hidden = true;
        result.innerHTML = '';
        button.disabled = true;
        button.innerHTML = buttonHtml;
    }

    function showFileError(message) {
        input.value = '';
        button.disabled = true;
        error.textContent = message;
        error.hidden = false;
    }

    // «Importar» del panel: se cierra el panel y se abre la ventana
    $('#btnExcelOpenImport').on('click', function () {
        var panel = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (panel) {
            offcanvasEl.addEventListener('hidden.bs.offcanvas', function () {
                reset();
                modal.show();
            }, {once: true});
            panel.hide();
        } else {
            reset();
            modal.show();
        }
    });

    // Solo Excel (.xlsx / .xls) y hasta 5 MB; el botón se habilita únicamente con un archivo válido
    input.addEventListener('change', function () {
        error.hidden = true;
        result.hidden = true;
        var file = input.files && input.files[0];
        if (!file) {
            button.disabled = true;
            return;
        }
        if (!/\.(xlsx|xls)$/i.test(file.name)) {
            return showFileError('Solo se permiten archivos de Excel (.xlsx o .xls).');
        }
        if (file.size > MAX_SIZE) {
            return showFileError('El archivo supera el máximo de 5 MB.');
        }
        if (file.size === 0) {
            return showFileError('El archivo está vacío.');
        }
        button.disabled = false;
    });

    function renderTable(title, rows, css) {
        if (!rows.length) {
            return '';
        }
        var html = '<div class="fw-bold mt-3 mb-1 ' + css + '">' + title + ' (' + rows.length + ')</div>' +
            '<div class="table-responsive" style="max-height: 240px; overflow-y: auto;">' +
            '<table class="table table-sm table-bordered mb-0"><thead><tr><th style="width:70px;">Fila</th>' +
            '<th style="width:150px;">Documento</th><th>Motivo</th></tr></thead><tbody>';
        rows.forEach(function (r) {
            html += '<tr><td>' + escapeHtml(r.row) + '</td><td>' + escapeHtml(r.dni || '—') + '</td><td>' +
                escapeHtml(r.message) + '</td></tr>';
        });
        return html + '</tbody></table></div>';
    }

    function showResult(data) {
        var html = '<div class="alert alert-' + (data.created ? 'success' : 'warning') + ' mb-0">' +
            '<b>' + data.created + '</b> de <b>' + data.total + '</b> ' + entity + ' creados.' +
            (data.skipped.length ? ' ' + data.skipped.length + ' ya existían (omitidos).' : '') +
            (data.errors.length ? ' ' + data.errors.length + ' con errores.' : '') + '</div>';
        (data.notes || []).forEach(function (note) {
            html += '<div class="small text-muted mt-2"><i class="fas fa-info-circle"></i> ' + escapeHtml(note) + '</div>';
        });
        html += renderTable('No se importaron por errores — corrija estas filas y vuelva a importar', data.errors, 'text-danger');
        html += renderTable('Omitidos: ya existen en el sistema', data.skipped, 'text-secondary');
        result.innerHTML = html;
        result.hidden = false;
    }

    button.addEventListener('click', function () {
        var file = input.files && input.files[0];
        if (!file) {
            return;
        }
        var body = new FormData();
        body.append('file', file);
        button.disabled = true;
        input.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Importando...';
        result.hidden = true;

        fetch(modalEl.dataset.importUrl, {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            body: body,
            credentials: 'same-origin'
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok && !data.error) {
                    data.error = 'No se pudo importar el archivo.';
                }
                return data;
            });
        }).then(function (data) {
            if (data.error) {
                return showFileError(data.error);
            }
            showResult(data);
            input.value = '';
            if (data.created && $.fn.DataTable.isDataTable('#data')) {
                $('#data').DataTable().ajax.reload(null, false);   // la lista muestra los registros nuevos
            }
        }).catch(function () {
            showFileError('No se pudo conectar con el servidor. Intente de nuevo.');
        }).then(function () {
            input.disabled = false;
            button.innerHTML = buttonHtml;
            button.disabled = !(input.files && input.files[0]);
        });
    });

    modalEl.addEventListener('hidden.bs.modal', reset);
});
