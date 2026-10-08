var employee = {
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
                {data: "dni"},
                {data: "names"},
                {data: "phone"},
                {data: "contract_type"},
                {data: "eps"},
                {data: "afp"},
                {data: "arl"},
                {data: "salary"},
                {data: "is_active"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + parseFloat(data).toLocaleString('es-CL');
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (data) {
                            return '<span class="badge bg-success rounded-pill">ACTIVO</span>';
                        }
                        return '<span class="badge bg-warning rounded-pill">INACTIVO</span>';
                    }
                },
                {
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
        $('#data thead th').css('background-color', '#ffffff');
    }
};

$(function () {
    employee.list();
});