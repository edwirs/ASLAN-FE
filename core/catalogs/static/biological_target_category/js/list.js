var category = {
    list: function () {
        $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'action': 'search'
                },
                dataSrc: ""
            },
            columns: [
                {data: "id"},
                {data: "name"},
                {data: "description"},
                {data: "handle_traps"}, // Columna 3
                {data: "id"},           // Columna 4 (Acciones)
            ],
            columnDefs: [
                {
                    // Renderizado para la columna handle_traps (índice 3)
                    targets: [3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (data) {
                            return '<span class="badge" style="background-color: #28a745; color: white; border-radius: 50px; padding: 5px 12px;">SI</span>';
                        } else {
                            return '<span class="badge" style="background-color: #fd7e14; color: white; border-radius: 50px; padding: 5px 12px;">NO</span>';
                        }
                    }
                },
                {
                    // Renderizado para acciones (índice 4)
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a href="' + pathname + 'update/' + row.id + '/" data-bs-toggle="tooltip" title="Editar" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a> ';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" data-bs-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></a>';
                        return buttons;
                    }
                },
            ],
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {
                enable_tooltip();
            }
        });
    }
};

$(function () {
    category.list();
});