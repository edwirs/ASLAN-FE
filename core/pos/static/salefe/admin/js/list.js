var tblSale;
var input_date_range;
var select_paymentmethod;
var select_transfermethods;
var select_service_type;
var input_cash, input_change;
var CAN = {edit: false, validate: false, radian: false};
try { CAN = JSON.parse(document.getElementById('can-data').textContent); } catch (e) { /* sin permisos extra */ }

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
                            dianIcon = '<span class="status-chip status-danger" data-bs-toggle="tooltip" title="El último intento de validación falló. Puede editarla y volver a validarla"><i class="fas fa-times"></i></span>';
                        } else {
                            dianIcon = '<span class="status-chip status-warning" data-bs-toggle="tooltip" title="Guardada en el sistema. Aún no se ha enviado a la DIAN (use «Validar»)"><i class="fas fa-clock"></i></span>';
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
                        var validated = !!row.validated;
                        var buttons = '<div class="d-inline-flex align-items-center gap-2">';
                        // Facturas que aún no se han enviado a la DIAN: botón «Validar» al lado de los 3 puntos
                        if (!validated && CAN.validate) {
                            buttons += '<button type="button" class="btn btn-success btn-validate" rel="validate" data-id="' + row.id + '" title="Enviar esta factura a la DIAN por Factus"><i class="fas fa-paper-plane"></i> Validar</button>';
                        }
                        buttons += '<div class="dropdown d-inline-block">';
                        buttons += '<button class="btn btn-actions-dots" type="button" data-bs-toggle="dropdown" aria-expanded="false"><i class="fas fa-ellipsis-h"></i></button>';
                        buttons += '<ul class="dropdown-menu dropdown-menu-end actions-dropdown-menu">';
                        if (row.editable && CAN.edit) {
                            buttons += '<li><a class="dropdown-item" href="' + pathname + 'update/' + row.id + '/"><i class="fas fa-edit text-warning"></i>Editar</a></li>';
                        }
                        if (validated) {
                            buttons += '<li><a class="dropdown-item" href="#" rel="print" data-id="' + row.id + '"><i class="fas fa-print text-secondary"></i>Imprimir</a></li>';
                            buttons += '<li><a class="dropdown-item" href="#" rel="view_invoice" data-url="' + (row.factus_pdf_url || '') + '"><i class="fas fa-eye text-info"></i>Ver factura</a></li>';
                            buttons += '<li><a class="dropdown-item" href="#" rel="resend_email" data-id="' + row.id + '"><i class="fas fa-envelope text-primary"></i>Enviar factura al correo</a></li>';
                            buttons += '<li><a class="dropdown-item" href="#" rel="download_pdf" data-id="' + row.id + '"><i class="fas fa-file-pdf text-danger"></i>Descargar PDF</a></li>';
                            if (CAN.radian) {
                                buttons += '<li><a class="dropdown-item" href="#" rel="radian" data-id="' + row.id + '" data-number="' + (row.factus_invoice_id || '') + '"><i class="fas fa-shield-halved text-success"></i>Eventos RADIAN</a></li>';
                            }
                        }
                        buttons += '</ul></div></div>';

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

var radian = {
    saleId: null,
    esc: function (t) { return $('<div>').text(t === null || t === undefined ? '' : t).html(); },

    open: function (id, number) {
        var self = this;
        self.saleId = id;
        $('#radianNumber').text(number ? 'Factura ' + number : '');
        $('#radianLoading').show();
        $('#radianError').hide();
        $('#radianContent').hide();
        $('#modalRadian').modal('show');
        $.ajax({
            url: pathname, type: 'POST', dataType: 'json', timeout: 40000,
            headers: {'X-CSRFToken': csrftoken},
            data: {action: 'radian_events', id: id},
            success: function (data) {
                $('#radianLoading').hide();
                if (data.error) {
                    return $('#radianError').text(data.error).show();
                }
                self.render(data);
            },
            error: function () {
                $('#radianLoading').hide();
                $('#radianError').text('No fue posible consultar a Factus. Intente de nuevo en unos minutos.').show();
            }
        });
    },

    // Los 5 eventos RADIAN, en el orden del tablero
    STEPS: [
        ['030', 'Acuse de recibo de Factura Electrónica de Venta'],
        ['032', 'Recibo del bien o prestación del servicio'],
        ['031', 'Reclamo de la Factura Electrónica de Venta'],
        ['033', 'Aceptación expresa'],
        ['034', 'Aceptación tácita']
    ],

    money: function (n) { return '$' + (parseFloat(n) || 0).toLocaleString('es-CO', {minimumFractionDigits: 2, maximumFractionDigits: 2}); },

    render: function (data) {
        var self = this;
        var inv = data.invoice || {};
        $('#radianDni').text(inv.dni || '—');
        $('#radianClient').text(inv.client || '—');
        $('#radianDate').text(inv.date || '—');
        $('#radianForm').text(inv.payment_form || '—');
        $('#radianMethod').text(inv.payment_method || '—');
        $('#radianDue').text(inv.due_date || '');
        $('#radianDueRow').toggle(!!inv.due_date);
        $('#radianTotal').text(self.money(inv.total));
        $('#radianCufe').text(inv.cufe ? 'CUFE: ' + inv.cufe : '').toggle(!!inv.cufe);
        $('#radianTitleValue').toggle(!!data.title_value);
        $('#radianNoTitle').toggle(!data.title_value);

        var colors = {accepted: 'bg-success', claim: 'bg-danger', received: 'bg-info', none: 'bg-secondary'};
        $('#radianBadge').attr('class', 'badge ' + (colors[data.summary.level] || 'bg-secondary')).text(data.summary.label);

        var byCode = {};
        data.events.forEach(function (e) { if (!byCode[e.code]) { byCode[e.code] = e; } });
        var $board = $('#radianBoard').empty();
        self.STEPS.forEach(function (step) {
            var code = step[0], event = byCode[code];
            var done = !!event;
            var iconColor = done ? (code === '031' ? 'text-danger' : 'text-success') : 'pending';
            var when = done ? self.esc(event.time || '') + '<br>' + self.esc(event.date || '') : '';
            var canEmit = code === '034' && !!data.can_tacit;
            var why = code !== '034' ? 'Este evento lo emite el cliente (el adquirente)'
                : (!data.is_credit ? 'La aceptación tácita solo aplica a facturas a crédito' : (done ? 'Ya está emitida' : 'La factura ya tiene una aceptación'));
            $board.append(
                '<div class="radian-step" data-code="' + code + '">' +
                '<div class="radian-step-name">' + self.esc(step[1]) + '</div>' +
                '<div class="radian-step-when">' + when + '</div>' +
                '<div class="radian-step-icon ' + iconColor + '"><i class="far fa-circle-check"></i></div>' +
                '<span ' + (canEmit ? '' : 'title="' + self.esc(why) + '"') + '><button type="button" class="btn btn-primary btn-sm radian-emit" data-code="' + code + '" ' +
                (canEmit ? '' : 'disabled') + '>Emitir</button></span></div>');
        });
        // El formulario de aceptación tácita se abre con «Emitir»; al refrescar vuelve a quedar cerrado
        $('#radianTacit').hide();
        $('#radianContent').show();
    },

    openTacit: function () {
        try {
            var saved = JSON.parse(localStorage.getItem('aslan-radian-person') || '{}');
            $('#tacitDocType').val(saved.type || '13'); $('#tacitId').val(saved.id || ''); $('#tacitDv').val(saved.dv || '');
            $('#tacitFirst').val(saved.first || ''); $('#tacitLast').val(saved.last || '');
            $('#tacitJob').val(saved.job || ''); $('#tacitDept').val(saved.dept || '');
        } catch (e) { /* sin almacenamiento */ }
        $('#radianTacit').show();
        $('#tacitId').trigger('focus');
    },

    registerTacit: function () {
        var self = this;
        var person = {
            identification_document_code: $('#tacitDocType').val(), identification: $.trim($('#tacitId').val()), dv: $.trim($('#tacitDv').val()),
            first_name: $.trim($('#tacitFirst').val()), last_name: $.trim($('#tacitLast').val()),
            job_title: $.trim($('#tacitJob').val()), organization_department: $.trim($('#tacitDept').val())
        };
        if (!person.identification || !person.first_name || !person.last_name) {
            return message_error('Escriba el número de documento, los nombres y los apellidos de quien registra el evento');
        }
        try {
            localStorage.setItem('aslan-radian-person', JSON.stringify({type: person.identification_document_code, id: person.identification,
                dv: person.dv, first: person.first_name, last: person.last_name, job: person.job_title, dept: person.organization_department}));
        } catch (e) { /* sin almacenamiento */ }
        dialog_action({
            'content': '¿Registrar la aceptación tácita de esta factura ante la DIAN? Esta acción no se puede deshacer.',
            'success': function () {
                $('#btnRadianTacit').prop('disabled', true);
                $.ajax({
                    url: pathname, type: 'POST', dataType: 'json', timeout: 60000,
                    headers: {'X-CSRFToken': csrftoken},
                    data: $.extend({action: 'radian_tacit', id: self.saleId}, person),
                    success: function (data) {
                        $('#btnRadianTacit').prop('disabled', false);
                        if (data.error) {
                            return Swal.fire({icon: 'error', title: 'No se pudo registrar el evento', text: data.error});
                        }
                        toastr.success(data.message);
                        self.render(data);
                    },
                    error: function () {
                        $('#btnRadianTacit').prop('disabled', false);
                        Swal.fire({icon: 'error', title: 'No se pudo registrar el evento', text: 'No hubo respuesta del servidor.'});
                    }
                });
            },
            'cancel': function () {}
        });
    }
};

$(function () {
    $('#btnRadianTacit').on('click', function () { radian.registerTacit(); });
    $('#radianBoard').on('click', '.radian-emit', function () { if ($(this).data('code') === '034') { radian.openTacit(); } });
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
        .on('click', 'button[rel="validate"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();
            var $btn = $(this);
            var id = $btn.data('id');
            var row = tblSale.rows().data().toArray().filter(function (r) { return r.id === id; })[0] || {};
            var who = (row.client && row.client.names) ? row.client.names : 'el cliente';
            dialog_action({
                'content': '¿Validar la factura #' + id + ' de ' + $('<div>').text(who).html() + ' por $' + parseFloat(row.total || 0).toLocaleString('es-CL') +
                    '? Se enviará a la DIAN y, una vez validada, ya no podrá editarse ni eliminarse.',
                'success': function () {
                    $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Validando...');
                    $.ajax({
                        url: pathname, type: 'POST', dataType: 'json', timeout: 90000,
                        headers: {'X-CSRFToken': csrftoken},
                        data: {action: 'validate', id: id},
                        success: function (data) {
                            if (data.error) {
                                $btn.prop('disabled', false).html('<i class="fas fa-paper-plane"></i> Validar');
                                Swal.fire({icon: 'error', title: 'No se pudo validar la factura', text: data.error});
                                return;
                            }
                            toastr.success(data.message);
                            (data.warnings || []).forEach(function (w) { toastr.warning(w); });
                            sale.list(false);
                        },
                        error: function () {
                            $btn.prop('disabled', false).html('<i class="fas fa-paper-plane"></i> Validar');
                            Swal.fire({icon: 'error', title: 'No se pudo validar la factura',
                                       text: 'No hubo respuesta del servidor. Revise el listado antes de reintentar: la factura pudo haberse validado.'});
                            sale.list(false);
                        }
                    });
                },
                'cancel': function () {}
            });
        })
        .on('click', 'a[rel="radian"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();
            radian.open($(this).data('id'), $(this).data('number'));
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
