var block = {

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
                    action: 'search'
                },

                dataSrc: ""
            },

            columns: [

                {"data": "code"},
                {"data": "name"},
                {"data": "has_sides"},
                {"data": "is_active"},
                {"data": "id"},
            ],

            columnDefs: [

                {
                    targets: [2],
                    className: 'text-center',
                    render: function (data) {

                        return data
                            ? '<span class="badge bg-success">Sí</span>'
                            : '<span class="badge bg-secondary">No</span>';
                    }
                },

                {
                    targets: [3],
                    className: 'text-center',
                    render: function (data) {

                        return data
                            ? '<span class="badge bg-success">Activo</span>'
                            : '<span class="badge bg-danger">Inactivo</span>';
                    }
                },

                {
                    targets: [-1],
                    className: 'text-center',
                    orderable: false,

                    render: function (data, type, row) {

                        let buttons = '';

                        // CORRECCIÓN AQUÍ: Ajustado a 'structure/update/' para coincidir con tu urls.py
                        buttons +=
                            '<a href="' + pathname + 'structure/update/' + row.id + '/" ' +
                            'class="btn btn-warning btn-sm me-1">' +
                            '<i class="fas fa-edit"></i>' +
                            '</a>';

                        buttons +=
                            '<a href="' + pathname + 'detail/' + row.id + '/" ' +
                            'class="btn btn-info btn-sm me-1">' +
                            '<i class="fas fa-sitemap"></i>' +
                            '</a>';

                        buttons +=
                            '<a href="' + pathname + 'delete/' + row.id + '/" ' +
                            'class="btn btn-danger btn-sm">' +
                            '<i class="fas fa-trash"></i>' +
                            '</a>';

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

    block.list();

});