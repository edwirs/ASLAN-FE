var tblSale;
var input_date_range;
var select_paymentmethod;
var select_transfermethods;
var select_service_type;
var input_cash, input_change;

var sale = {
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
        tblSale = $('#data').DataTable({
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
                {data: "factus_invoice_id"},
                {data: "client.names"},
                {data: "date_joined"},
                {data: "total"},
                {data: "paymentmethod.name"},
                {data: "factus_status"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + parseFloat(data).toLocaleString('es-CL');
                    }
                },
                {
                    targets: [-3],
                    class: 'text-center',
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
                        buttons += '<li><a class="dropdown-item" href="#" rel="view_invoice" data-url="' + (row.factus_pdf_url || '') + '"><i class="fas fa-eye text-info"></i>Ver factura</a></li>';
                        buttons += '<li><a class="dropdown-item" href="#" rel="resend_email" data-id="' + row.id + '"><i class="fas fa-envelope text-primary"></i>Enviar factura al correo</a></li>';
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
    select_paymentmethod = $('select[name="paymentmethod"]');
    select_transfermethods = $('select[name="transfermethods"]');
    select_service_type = $('select[name="service_type"]');
    input_cash = $('input[name="cash"]');
    input_change = $('input[name="change"]');
    input_propina = $('input[name="propina"]');

    $('#data tbody')
        .off()
        .on('click', 'a[rel="myModalEdit"]', function () {
            $('.tooltip').remove();

            let id = $(this).data('id');
            $.ajax({
                url: '/pos/salefe/admin/get_sale_Fe/' + id + '/',
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    if (!data.error) {
                        // Cargar datos en el modal
                        $('#myModalEdit').data('sale-id', data.id);
                        $('#myModalEdit #id_paymentmethod').val(data.paymentmethod.id).trigger('change');
                        $('#myModalEdit #id_transfermethods').val(data.transfermethods.id).trigger('change');
                        $('#myModalEdit #id_total').val(data.total).toLocaleString('es-CL');
                        $('#myModalEdit #id_cash').val(data.cash).toLocaleString('es-CL');
                        $('#myModalEdit #id_change').val(data.change).toLocaleString('es-CL');
                        $('#myModalEdit #id_propina').val(data.propina).toLocaleString('es-CL');

                        // Mostrar modal
                        $('#myModalEdit').modal('show');
                    } else {
                        alert(data.error);
                    }
                }
            });
        })
        .on('click', 'a[rel="print"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            let id = $(this).data('id');
            let printUrl = pathname + 'print/invoice/' + id + '/';

            var iframe = document.getElementById('print_frame');
            iframe.src = printUrl;

            iframe.onload = function () {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();

                // Cuando el usuario termina (imprimir o cancelar), regresar al listado
                var afterPrint = function () {
                    location.href = pathname;  // vuelve a la lista
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
                return message_error('Esta factura aún no ha sido validada por Factus');
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
            $('#myModalResendEmail').data('sale-id', id);
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
        var id = $('#myModalResendEmail').data('sale-id');
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
                sale.list(false);
            },
            error: function () {
                message_error('Ocurrió un error al reenviar el correo');
            }
        });
    });

    // Guardar cambios al dar clic en "Guardar"
    $(document).on('click', '#btnSaveEdit', function () {
        let id = $('#myModalEdit').data('sale-id'); // guardamos el id de la venta al abrir la modal

        // Serializar los campos del formulario
        let formData = {
            paymentmethod: $('#id_paymentmethod').val(),
            transfermethods: $('#id_transfermethods').val(),
            typemethods: $('#id_typemethods').val(),
            total: $('#id_total').val(),
            cash: $('#id_cash').val(),
            change: $('#id_change').val(),
            propina: $('#id_propina').val(),
        };

        $.ajax({
            url: '/pos/salefe/admin/update_sale_Fe/' + id + '/',  // nueva URL para actualizar
            type: 'POST', // puede ser PUT si quieres, pero en Django normalmente usamos POST
            data: formData,
            headers: { "X-CSRFToken": csrftoken }, // csrf_token necesario
            success: function (data) {
                console.log(formData);
                if (!data.error) {
                    toastr.success('La factura se guardó exitosamente');
                        setTimeout(function() {
                            $('#myModalEdit').modal('hide');
                            location.reload();
                        }, 1000);
                } else {
                    alert("Error: " + data.error);
                }
            },
            error: function (xhr, status, error) {
                console.error(error);
                alert("Ocurrió un error al guardar los cambios ❌");
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
            sale.list(false);
        });

    $('.drp-buttons').hide();

    sale.list(false);

    $('.btnSearchAll').on('click', function () {
        sale.list(true);
    });

    $('#data tbody').on('change', '.delivered-switch', function () {
        const saleId = $(this).data('id');
        const isChecked = $(this).is(':checked');

        fetch(pathname + 'delivered/' + saleId + '/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
            }
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                alert('Error al actualizar el estado de entrega.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });

    $('select[name="paymentmethod"]').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    $('select[name="transfermethods"]').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    select_paymentmethod.select2({
        theme: "bootstrap4",
        language: 'es'
    });

    select_transfermethods.select2({
        theme: "bootstrap4",
        language: 'es'
    });

    select_service_type.select2({
        theme: "bootstrap4",
        language: 'es'
    });

    select_transfermethods.parent().hide();

    select_paymentmethod.on('change', function(){
        const selectedValue = $(this).val();
        select_transfermethods.empty();
        if (selectedValue === 'transfer') {
            select_transfermethods.append('<option value="nequi">Nequi</option>');
            select_transfermethods.append('<option value="daviplata">Daviplata</option>');
            select_transfermethods.parent().show();
        } else if (selectedValue === 'mixto') {
        select_transfermethods.append('<option value="mixto1">Nequi + Efectivo</option>');
        select_transfermethods.append('<option value="mixto2">Daviplata + Efectivo</option>');
        select_transfermethods.append('<option value="mixto3">Nequi + Daviplata</option>');
        select_transfermethods.parent().show();
        } else {
            select_transfermethods.parent().hide();
        }
    });

    input_cash
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            let cash = parseFloat($(this).val()) || 0;              // lo que el usuario digitó
            let total = $('#myModalEdit #id_total').val() || 0; // el total de la venta
            let change = cash - total;                              // diferencia

            // Si el cambio es negativo, lo dejamos en 0 (opcional)
            if (change < 0) {
                change = 0;
            }

            // Asignar valor al campo change
            $('#myModalEdit #id_change').val(change);
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    input_propina
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            sale.calculateInvoice();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

});
