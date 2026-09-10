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
                {data: "factus_status"},
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
                        var dianIcon;
                        if (row.factus_cufe) {
                            dianIcon = '<span class="status-chip status-success" data-bs-toggle="tooltip" title="Validada por la DIAN"><i class="fas fa-check"></i></span>';
                        } else if (row.factus_status === 'error') {
                            dianIcon = '<span class="status-chip status-danger" data-bs-toggle="tooltip" title="Rechazada por Factus / DIAN"><i class="fas fa-times"></i></span>';
                        } else {
                            dianIcon = '<span class="status-chip status-warning" data-bs-toggle="tooltip" title="Pendiente de validación"><i class="fas fa-clock"></i></span>';
                        }

                        var sentCount = parseInt(row.email_sent_count) || 0;
                        var emailIcon;
                        if (sentCount === 0) {
                            emailIcon = '<span class="status-chip status-muted" data-bs-toggle="tooltip" title="El correo aún no se ha enviado"><i class="fas fa-envelope"></i></span>';
                        } else if (sentCount >= 4) {
                            emailIcon = '<span class="status-chip status-warning" data-bs-toggle="tooltip" title="Correo enviado (' + sentCount + '/4) — límite alcanzado"><i class="fas fa-envelope"></i></span>';
                        } else {
                            emailIcon = '<span class="status-chip status-success" data-bs-toggle="tooltip" title="Correo enviado exitosamente (' + sentCount + '/4)"><i class="fas fa-envelope"></i></span>';
                        }

                        return '<div class="d-flex justify-content-center align-items-center gap-2">' + dianIcon + emailIcon + '</div>';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<div class="dropdown d-inline-block">';
                        buttons += '<button class="btn btn-actions-dots" type="button" data-bs-toggle="dropdown" aria-expanded="false"><i class="fas fa-ellipsis-h"></i></button>';
                        buttons += '<ul class="dropdown-menu dropdown-menu-end actions-dropdown-menu">';
                        buttons += '<li><a class="dropdown-item" href="#" rel="print" data-id="' + row.id + '"><i class="fas fa-print text-secondary"></i>Imprimir</a></li>';
                        buttons += '<li><a class="dropdown-item" href="#" rel="view_invoice" data-url="' + (row.factus_pdf_url || '') + '"><i class="fas fa-eye text-info"></i>Ver nota</a></li>';
                        buttons += '<li><a class="dropdown-item" href="#" rel="resend_email" data-id="' + row.id + '"><i class="fas fa-envelope text-primary"></i>Enviar nota al correo</a></li>';
                        buttons += '<li><a class="dropdown-item" href="#" rel="download_pdf" data-id="' + row.id + '"><i class="fas fa-file-pdf text-danger"></i>Descargar PDF</a></li>';
                        buttons += '</ul></div>';

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
        .on('click', 'a[rel="view_invoice"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            var url = $(this).data('url');
            if (!url) {
                return message_error('Esta nota crédito aún no ha sido validada por Factus');
            }
            window.open(url, '_blank');
        })
        .on('click', 'a[rel="download_pdf"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            let id = $(this).data('id');
            window.location.href = pathname + 'download/pdf/' + id + '/';
        })
        .on('click', 'a[rel="resend_email"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            let id = $(this).data('id');
            $('#myModalResendEmail').data('credit-note-id', id);
            $.ajax({
                url: pathname,
                type: 'POST',
                headers: {'X-CSRFToken': csrftoken},
                data: {action: 'get_client_emails', id: id},
                dataType: 'json',
                success: function (data) {
                    if (data.error) {
                        return message_error(data.error);
                    }
                    $('#resendClientName').val(data.client_name);
                    var $list = $('#resendEmailList').empty();
                    if (!data.emails.length) {
                        $list.append('<p class="text-muted mb-0">Este cliente no tiene correos electrónicos registrados.</p>');
                        $('#btnConfirmResendEmail').prop('disabled', true);
                    } else {
                        $('#btnConfirmResendEmail').prop('disabled', false);
                        data.emails.forEach(function (item, index) {
                            $list.append(
                                '<div class="form-check">' +
                                '<input class="form-check-input" type="radio" name="resend_email_option" id="resendEmailOpt' + index + '" value="' + item.value + '" ' + (index === 0 ? 'checked' : '') + '>' +
                                '<label class="form-check-label" for="resendEmailOpt' + index + '">' + item.label + '</label>' +
                                '</div>'
                            );
                        });
                    }
                    $('#myModalResendEmail').modal('show');
                },
                error: function () {
                    message_error('Ocurrió un error al consultar los correos del cliente');
                }
            });
        });

    $('#btnConfirmResendEmail').on('click', function () {
        var id = $('#myModalResendEmail').data('credit-note-id');
        var email = $('input[name="resend_email_option"]:checked').val();
        if (!email) {
            return message_error('Seleccione un correo de destino');
        }
        $.ajax({
            url: pathname,
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            data: {action: 'resend_email', id: id, email: email},
            dataType: 'json',
            success: function (data) {
                if (data.error) {
                    return message_error(data.error);
                }
                $('#myModalResendEmail').modal('hide');
                toastr.success(data.message || 'Correo reenviado exitosamente');
                creditNote.list(false);
            },
            error: function () {
                message_error('Ocurrió un error al reenviar el correo');
            }
        });
    });

    input_date_range.daterangepicker({
                language: 'auto',
                startDate: moment().subtract(6, 'days'),
                endDate: moment(),
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
