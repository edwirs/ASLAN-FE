var trap = {
    initTable: function(tableId, actionUrl, columns) {
        // Verificamos si el elemento existe antes de inicializar
        if ($('#' + tableId).length === 0) return;

        return $('#' + tableId).DataTable({
            destroy: true,
            responsive: true,
            autoWidth: false,
            serverSide: false, // Cambiar a true si el volumen de datos es muy alto
            ajax: {
                url: window.location.pathname,
                type: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                data: { 'action': actionUrl },
                dataSrc: ""
            },
            columns: columns,
            columnDefs: [
                {
                    targets: [-1], // Columna de Opciones
                    class: 'text-center',
                    orderable: false,
                    render: function(data, type, row) {
                        // data es el ID, pero pasamos la fila completa o usamos el row
                        return `<button type="button" class="btn btn-warning btn-sm btn-flat btn-edit" data-action="edit_ica">
                                    <i class="fas fa-edit"></i>
                                </button>
                                `;
                    }
                },
                {
                    targets: [-2], // Columna de Estado
                    class: 'text-center',
                    orderable: true,
                    render: function(data, type, row) {
                        return data 
                            ? '<span class="badge bg-success">Activo</span>' 
                            : '<span class="badge bg-danger">Inactivo</span>';
                    }
                }
            ],
            language: {
                url: "//cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json" // Carga idioma español
            }
        });
    }
};

$(function () {
    const cols = [
        { data: "id" }, 
        { data: "name" }, 
        { data: "observation" }, 
        { data: "is_active" }, 
        { data: "id" }
    ];

    const colsIn = [
        { data: "id" },
        { data: "block.name" }, // Nueva columna de bloque
        { data: "name" }, 
        { data: "observation" }, 
        { data: "is_active" }, 
        { data: "id" }
    ];
    
    // Inicializar la primera tabla al cargar
    trap.initTable('data_ica', 'search_ica', cols);
    
    // Escuchar el evento de cambio de pestaña para cargar la segunda solo cuando sea necesario
    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        var target = $(e.target).attr("href"); // Obtiene el ID de la pestaña activa
        
        if (target === "#copi_tab" && !$.fn.DataTable.isDataTable('#data_copi')) {
            trap.initTable('data_copi', 'search_copitarsia', cols);
        }
    });
    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        var target = $(e.target).attr("href"); // Obtiene el ID de la pestaña activa
        
        if (target === "#in_tab" && !$.fn.DataTable.isDataTable('#data_in')) {
            trap.initTable('data_in', 'search_in', colsIn);
        }
    });
    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        var target = $(e.target).attr("href"); // Obtiene el ID de la pestaña activa
        
        if (target === "#out_tab" && !$.fn.DataTable.isDataTable('#data_out')) {
            trap.initTable('data_out', 'search_out', cols);
        }
    });
});

function openModal(actionType, url = null, data = null) {
    $('#frmTrap')[0].reset();
    $('#action').val(actionType);

    // Mostrar u ocultar el selector de bloque según la acción
    if (actionType === 'add_in' || (data && actionType === 'edit_in')) {
        $('#block_container').show();
        if(data) $('#block_id').val(data.block.id); // Cargar ID si es edición
    } else {
        $('#block_container').hide();
    }
    
    // Si pasamos datos (edición), los cargamos
    if (data) {
        $('#name').val(data.name);
        $('#observation').val(data.observation);
        $('#is_active').prop('checked', data.is_active);
    }
    
    $('#modalTrap').modal('show');
}

// Delegación de eventos para el botón editar
$('body').on('click', '.btn-edit', function(e) {
    e.preventDefault();
    var tr = $(this).closest('tr');
    var row = $(this).closest('table').DataTable().row(tr).data();
    
    // Identificamos el tipo basado en el ID de la tabla desde donde se hace clic
    var tableId = $(this).closest('table').attr('id');
        const actionMap = {
        'data_ica': 'edit_ica',
        'data_copi': 'edit_copi',
        'data_in': 'edit_in',
        'data_out': 'edit_out'
    };
    var action = actionMap[tableId] || 'default_action';
    //var action = (tableId === 'data_ica') ? 'edit_ica' : 'edit_copi';
    
    // Si la tabla es la de internas, mostramos el campo
    if(tableId === 'data_in') {
        $('#block_container').show();
        $('#block_id').val(row.block.id);
    } else {
        $('#block_container').hide();
    }

    // Abrir modal pasando los datos y la acción calculada
    $('#id').val(row.id); // Llenamos el ID oculto
    $('#name').val(row.name);
    $('#observation').val(row.observation);
    $('#is_active').prop('checked', row.is_active);
    
    $('#action').val(action);
    $('#modalTrap').modal('show');
});

$('#frmTrap').on('submit', function(e) {
    e.preventDefault();
    var parameters = new FormData(this);
    
    $.ajax({
        url: window.location.pathname,
        type: 'POST',
        data: parameters,
        dataType: 'json',
        processData: false,
        contentType: false,
        headers: {'X-CSRFToken': csrftoken},
        success: function(request) {
            if (!request.hasOwnProperty('error')) {
                $('#modalTrap').modal('hide');
                // Recargar las tablas
                $('#data_ica').DataTable().ajax.reload();
                if ($.fn.DataTable.isDataTable('#data_copi')) {
                    $('#data_copi').DataTable().ajax.reload();
                }
                else if ($.fn.DataTable.isDataTable('#data_in')) {
                    $('#data_in').DataTable().ajax.reload();
                }
                else if ($.fn.DataTable.isDataTable('#data_out')) {
                    $('#data_out').DataTable().ajax.reload();
                }
                return false;
            }
            alert(request.error);
        }
    });
});