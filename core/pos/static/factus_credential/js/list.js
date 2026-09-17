var tblFactusCredential;

var factusCredential = {
    list: function () {
        tblFactusCredential = $('#data').DataTable({
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
                {data: "environment.name"},
                {data: "api_url"},
                {data: "is_active"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.is_active) {
                            return '<span class="badge badge-success"><i class="fas fa-check"></i> Activa</span>';
                        }
                        return '<button type="button" class="btn btn-outline-secondary btn-sm" rel="activate" data-id="' + row.id + '">Activar</button>';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a href="' + pathname + 'update/' + row.id + '/" data-bs-toggle="tooltip" title="Editar" class="btn btn-warning btn-sm rounded-pill"><i class="fas fa-edit"></i></a> ';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" data-bs-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-sm rounded-pill"><i class="fas fa-trash"></i></a>';
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
    toastr.options = {
        "closeButton": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "timeOut": "3000",
        "extendedTimeOut": "1000"
    };

    factusCredential.list();

    $('#data tbody')
        .off()
        .on('click', 'button[rel="activate"]', function () {
            $('.tooltip').remove();
            let id = $(this).data('id');
            dialog_action({
                'content': 'Esta credencial pasará a ser la que use el sistema para conectarse a Factus. ¿Continuar?',
                'success': function () {
                    $.ajax({
                        url: pathname,
                        type: 'POST',
                        headers: {'X-CSRFToken': csrftoken},
                        data: {action: 'activate', id: id},
                        dataType: 'json',
                        success: function (data) {
                            if (data.error) {
                                return message_error(data.error);
                            }
                            toastr.success('Credencial activada exitosamente');
                            factusCredential.list();
                        },
                        error: function () {
                            message_error('Ocurrió un error al activar la credencial');
                        }
                    });
                },
                'cancel': function () {

                }
            });
        });
});
