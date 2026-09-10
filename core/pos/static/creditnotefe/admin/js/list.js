var tblCreditNote;
var input_date_range;

var creditNote = {
    list: function (all) {
        var parameters = {
            'action': 'search',
            'start_date': input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD'),
            'end_date': input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD'),
        };
        if (all) {
            parameters['start_date'] = '';
            parameters['end_date'] = '';
        }
        tblCreditNote = $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: parameters,
                dataSrc: ""
            },
            order: [[0, 'desc']],
            columns: [
                {data: "id"},
                {data: "factus_credit_note_number"},
                {data: "client.names"},
                {data: "correction_concept.name"},
                {data: "date_joined"},
                {data: "total"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + parseFloat(data).toLocaleString('es-CL');
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a rel="detail" data-bs-toggle="tooltip" title="Detalle" class="btn btn-success btn-sm rounded-pill"><i class="fas fa-boxes"></i></a> ';
                        buttons += '<a href="#" rel="print" data-id="' + row.id + '" data-bs-toggle="tooltip" title="Imprimir" class="btn btn-secondary btn-sm rounded-pill"><i class="fas fa-print"></i></a> ';
                        buttons += '<a href="#" rel="delete" data-id="' + row.id + '" data-bs-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-sm rounded-pill"><i class="fas fa-trash"></i></a>';

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
        $('#data thead th').css('background-color', '#ffffffff');
    }
};

$(function () {
    input_date_range = $('input[name="date_range"]');

    $('#data tbody')
        .off()
        .on('click', 'a[rel="detail"]', function () {
            $('.tooltip').remove();
            var tr = tblCreditNote.cell($(this).closest('td, li')).index();
            var row = tblCreditNote.row(tr.row).data();
            $('#tblProducts').DataTable({
                autoWidth: false,
                destroy: true,
                ajax: {
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        'action': 'search_detail_products',
                        'id': row.id
                    },
                    dataSrc: ""
                },
                columns: [
                    {data: "product.short_name"},
                    {data: "price_with_vat"},
                    {data: "cant"},
                    {data: "subtotal"},
                    {data: "total_dscto"},
                    {data: "total"},
                ],
                columnDefs: [
                    {
                        targets: [-1, -2, -3, -5],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '$' + parseFloat(data).toLocaleString('es-CL');
                        }
                    },
                    {
                        targets: [-4],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return data;
                        }
                    }
                ],
                initComplete: function (settings, json) {

                }
            });
            $('#myModalDetail').modal('show');
        })
        .on('click', 'a[rel="print"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            let id = $(this).data('id');
            let printUrl = pathname + 'print/' + id + '/';

            var iframe = document.getElementById('print_frame');
            iframe.src = printUrl;

            iframe.onload = function () {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();

                var afterPrint = function () {
                    location.href = pathname;
                    window.removeEventListener("afterprint", afterPrint);
                };
                window.addEventListener("afterprint", afterPrint);
            };
        })
        .on('click', 'a[rel="delete"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            let id = $(this).data('id');
            dialog_action({
                'content': '¿Estás seguro de eliminar esta nota crédito local?',
                'success': function () {
                    $.ajax({
                        url: pathname + 'delete/' + id + '/',
                        type: 'POST',
                        headers: {'X-CSRFToken': csrftoken},
                        success: function (data) {
                            if (!data.error) {
                                toastr.success('La nota crédito se eliminó exitosamente');
                                creditNote.list(false);
                            } else {
                                message_error(data.error);
                            }
                        }
                    });
                },
                'cancel': function () {

                }
            });
        });

    input_date_range.daterangepicker({
                language: 'auto',
                startDate: new Date(),
                locale: {
                    format: 'YYYY-MM-DD',
                },
                autoApply: true,
            }
        )
        .on('change.daterangepicker apply.daterangepicker', function (ev, picker) {
            creditNote.list(false);
        });

    $('.drp-buttons').hide();

    creditNote.list(false);

    $('.btnSearchAll').on('click', function () {
        creditNote.list(true);
    });

    toastr.options = {
        "closeButton": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "timeOut": "3000",
        "extendedTimeOut": "1000"
    };
});
