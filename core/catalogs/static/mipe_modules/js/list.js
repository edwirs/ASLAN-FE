var mipemodule = {
    list: function () {
        $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            responsive: true,
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
                {data: "order"},
                {data: "icon"},
                {data: "url_name"},
                {data: "is_active"},
                {data: "id"},
            ],
            columnDefs: [

                {
                    targets: [3],
                    className: 'text-center',
                    render: function (data, type, row) {
                        return '<i class="' + row.icon + ' fa-2x"></i>';
                    }
                },

                {
                    targets: [5],
                    className: 'text-center',
                    render: function (data, type, row) {

                        if (row.is_active) {
                            return '<span class="badge bg-success">Activo</span>';
                        }

                        return '<span class="badge bg-danger">Inactivo</span>';
                    }
                },

                {
                    targets: [-1],
                    className: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {

                        var buttons = '';

                        buttons += '<a href="' + pathname + 'update/' + row.id + '/" ';
                        buttons += 'class="btn btn-warning btn-sm" ';
                        buttons += 'data-bs-toggle="tooltip" ';
                        buttons += 'title="Editar">';
                        buttons += '<i class="fas fa-edit"></i></a> ';

                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" ';
                        buttons += 'class="btn btn-danger btn-sm" ';
                        buttons += 'data-bs-toggle="tooltip" ';
                        buttons += 'title="Eliminar">';
                        buttons += '<i class="fas fa-trash"></i></a>';

                        return buttons;
                    }
                }
            ],
            initComplete: function () {
                enable_tooltip();
            }
        });
    }
};

$(function () {
    mipemodule.list();
});