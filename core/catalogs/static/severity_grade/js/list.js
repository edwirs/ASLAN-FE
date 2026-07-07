var severityGrade = {
    list: function () {
        $('#data').DataTable({
            responsive: false,
            scrollX: true,
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
                {data: "category.name"},
                {data: "min_value"},
                {data: "max_value"},
                {data: "description"},
                {data: "is_active"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a href="' + pathname + 'update/' + row.id + '/" data-bs-toggle="tooltip" title="Editar" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a> ';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" data-bs-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></a>';
                        return buttons;
                    },
                    
                },
                {
                    targets: [-2],
                    className: 'text-center',
                    render: function (data, type, row) {
                        return data
                            ? '<span class="badge rounded-pill bg-primary px-3 py-2">ACTIVO</span>'
                            : '<span class="badge rounded-pill bg-secondary px-3 py-2">INACTIVO</span>';
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
    severityGrade.list();
});