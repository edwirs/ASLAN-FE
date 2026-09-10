var select_client;
var select_operation_type;
var select_correction_concept;
var select_paymentmethod;
var select_transfermethods;
var tblProducts;
var billing_period_start_date, billing_period_end_date;
var input_search_product, input_date_joined;
var input_nequi_value, input_daviplata_value;
var input_reference_bill_number, input_reference_cufe;

var lastInvoiceSearchResponse = null;

var creditNote = {
    detail: {
        subtotal_0: 0.00,
        subtotal_12: 0.00,
        subtotal_12_sin_iva: 0.00,
        subtotal: 0.00,
        dscto: 0.00,
        total_dscto: 0.00,
        iva: 0.00,
        total_iva: 0.00,
        total: 0.00,
        products: []
    },
    itemsEditable: true,
    calculateInvoice: function () {
        var tax = this.detail.iva / 100;

        this.detail.products.forEach(function (value, index, array) {
            var cant = parseFloat(value.cant) || 0;
            var pvp = parseFloat(value.pvp) || 0;
            var dscto = parseFloat(value.dscto) || 0;

            value.iva = parseFloat(tax);
            value.price_with_vat = pvp + (pvp * value.iva);
            value.subtotal = pvp * cant;
            value.total_dscto = value.subtotal * (dscto / 100);
            value.total_iva = (value.subtotal - value.total_dscto) * value.iva;
            value.total = value.subtotal - value.total_dscto;
        });

        this.detail.subtotal_0 = this.detail.products.filter(value => !value.with_tax).reduce((a, b) => a + (b.total || 0), 0);
        this.detail.subtotal_12 = this.detail.products.filter(value => value.with_tax).reduce((a, b) => a + (b.total || 0), 0);
        this.detail.subtotal = parseFloat(this.detail.subtotal_0) + parseFloat(this.detail.subtotal_12);

        this.detail.dscto = 0.00;
        this.detail.total_dscto = 0.00;
        this.detail.total_iva = this.detail.products.filter(value => value.with_tax).reduce((a, b) => a + (b.total_iva || 0), 0);
        this.detail.subtotal_12_sin_iva = this.detail.subtotal_12;
        this.detail.total = this.detail.subtotal + this.detail.total_iva;

        $('input[name="subtotal_0"]').val(this.detail.subtotal_0.toFixed(2));
        $('input[name="subtotal_12"]').val(this.detail.subtotal_12.toFixed(2));
        $('input[name="subtotal_12_sin_iva"]').val(this.detail.subtotal_12_sin_iva.toLocaleString('es-CL'));
        $('input[name="iva"]').val(this.detail.iva.toLocaleString('es-CL'));
        $('input[name="total_iva"]').val(this.detail.total_iva.toLocaleString('es-CL'));
        $('input[name="total_dscto"]').val(this.detail.total_dscto.toLocaleString('es-CL'));
        $('input[name="total"]').val(this.detail.total.toLocaleString('es-CL'));
    },
    addProduct: function (item) {
        if (!item.dscto) item.dscto = 0;
        this.detail.products.push(item);
        this.listProducts();
    },
    getProductIds: function () {
        return this.detail.products.map(value => value.id);
    },
    setProducts: function (items, editable) {
        this.detail.products = items;
        this.itemsEditable = editable;
        this.listProducts();
    },
    listProducts: function () {
        var self = this;
        this.calculateInvoice();
        tblProducts = $('#tblProducts').DataTable({
            autoWidth: false,
            destroy: true,
            data: this.detail.products,
            ordering: false,
            lengthChange: false,
            searching: false,
            paginate: false,
            columns: [
                {data: "id"},
                {data: "name"},
                {data: "cant"},
                {data: "dscto"},
                {data: "pvp"},
                {data: "total"},
            ],
            columnDefs: [
                {
                    targets: [0],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (!self.itemsEditable) return '<i class="fas fa-lock text-muted"></i>';
                        return '<a rel="remove" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></a>';
                    }
                },
                {
                    targets: [1],
                    class: 'text-left',
                    render: function (data, type, row) {
                        return data;
                    }
                },
                {
                    targets: [2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var disabled = self.itemsEditable ? '' : 'disabled';
                        return '<input type="number" step="1" min="1" class="form-control text-center" autocomplete="off" name="cant" value="' + row.cant + '" ' + disabled + '>';
                    }
                },
                {
                    targets: [3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var valDscto = row.dscto !== undefined ? row.dscto : 0;
                        var disabled = self.itemsEditable ? '' : 'disabled';
                        return '<input type="number" step="0.01" min="0" max="100" class="form-control text-center" autocomplete="off" name="dscto_unitary" value="' + valDscto + '" ' + disabled + '>';
                    }
                },
                {
                    targets: [4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var disabled = self.itemsEditable ? '' : 'disabled';
                        return '<input type="number" step="0.01" min="0" class="form-control text-center" autocomplete="off" name="pvp" value="' + row.pvp + '" ' + disabled + '>';
                    }
                },
                {
                    targets: [5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + parseFloat(data).toLocaleString('es-CL');
                    }
                }
            ],
            rowCallback: function (row, data, index) {
                var tr = $(row).closest('tr');
                tr.find('input[name="cant"], input[name="dscto_unitary"], input[name="pvp"]').on('keypress', function (e) {
                    return validate_text_box({'event': e, 'type': 'decimals'});
                });
            },
            initComplete: function (settings, json) {

            }
        });
    },
};

function flattenSaleDetail(detail) {
    return {
        id: detail.product.id,
        sale_detail_id: detail.id,
        name: detail.product.name,
        with_tax: detail.product.with_tax,
        cant: detail.cant,
        pvp: parseFloat(detail.price),
        dscto: parseFloat(detail.dscto) * 100,
    };
}

function isAnulacion() {
    return select_correction_concept.val() === '2';
}

function isWithReference() {
    return select_operation_type.val() === '20';
}

function refreshItemsLockState() {
    var locked = isAnulacion();
    $('#itemsLockedAlert').toggleClass('d-none', !locked || !isWithReference());

    if (isWithReference() && locked && lastInvoiceSearchResponse) {
        // La anulación debe reflejar EXACTAMENTE lo facturado: se reconstruye
        // desde la última respuesta de la factura buscada, descartando ediciones.
        creditNote.setProducts(lastInvoiceSearchResponse.details.map(flattenSaleDetail), false);
    } else {
        creditNote.itemsEditable = !locked;
        creditNote.listProducts();
    }
}

function toggleOperationTypeSections() {
    var withReference = isWithReference();

    $('#cardReferenceInvoice').toggleClass('d-none', !withReference);
    $('#cardBillingPeriod').toggleClass('d-none', withReference);
    $('#productSearchRow').toggleClass('d-none', withReference);

    if (withReference) {
        select_client.prop('disabled', true);
        $('#btnAddClientWrapper').addClass('d-none');
        billing_period_start_date.val('').prop('required', false);
        billing_period_end_date.val('').prop('required', false);
        input_reference_bill_number.prop('required', true);

        // Motivo por defecto al elegir "con referencia": Anulación de factura electrónica
        select_correction_concept.val('2').trigger('change');
    } else {
        select_client.prop('disabled', false);
        $('#btnAddClientWrapper').removeClass('d-none');
        input_reference_bill_number.prop('required', false);
        billing_period_start_date.prop('required', true);
        billing_period_end_date.prop('required', true);

        // Reset de datos ligados a una factura previamente buscada
        input_reference_bill_number.val('');
        input_reference_cufe.val('');
        lastInvoiceSearchResponse = null;
        select_client.val(null).trigger('change');
        $('#client_email').val('');

        // Motivo por defecto al elegir "sin referencia": Devolución parcial
        select_correction_concept.val('1').trigger('change');
    }

    creditNote.setProducts([], true);
}

$(function () {
    const rangeInput = $('input[name="numbering_range"]');
    const consecutiveInput = $('input[name="consecutive"]');

    if (rangeInput.length && typeof FACTUS_RANGE_DISPLAY !== 'undefined') {
        rangeInput.val(FACTUS_RANGE_DISPLAY);
        rangeInput.attr('readonly', true);
    }
    if (consecutiveInput.length && typeof FACTUS_CURRENT_CONSECUTIVE !== 'undefined') {
        consecutiveInput.val(FACTUS_CURRENT_CONSECUTIVE);
        consecutiveInput.attr('readonly', true);
    }

    select_client = $('select[name="client"]');
    select_operation_type = $('select[name="operation_type"]');
    select_correction_concept = $('select[name="correction_concept"]');
    select_paymentmethod = $('select[name="paymentmethod"]');
    select_transfermethods = $('select[name="transfermethods"]');
    input_search_product = $('input[name="search_product"]');
    input_date_joined = $('input[name="date_joined"]');
    billing_period_start_date = $('input[name="billing_period_start_date"]');
    billing_period_end_date = $('input[name="billing_period_end_date"]');
    input_nequi_value = $('input[name="nequi_value"]');
    input_daviplata_value = $('input[name="daviplata_value"]');
    input_reference_bill_number = $('input[name="reference_bill_number"]');
    input_reference_cufe = $('input[name="reference_cufe"]');

    // --- CONTADOR DE CARACTERES ---
    var maxLength = 500;
    var $textareaDesc = $('textarea[name="description"], #id_description');
    if ($textareaDesc.length) {
        $textareaDesc.attr('maxlength', maxLength);
        var $formGroup = $textareaDesc.closest('.form-group');
        var $label = $formGroup.find('label').first();
        if ($label.length) {
            $label.css({'display': 'flex', 'justify-content': 'space-between', 'align-items': 'center', 'width': '100%'});
            var $counter = $('#charCountDisplay');
            if ($counter.length && $counter.parent()[0] !== $label[0]) {
                $counter.detach().appendTo($label);
            }
        }
        function updateCharCount() {
            var textLength = $textareaDesc.val() ? $textareaDesc.val().length : 0;
            $('#charCountDisplay').text('(' + textLength + '/' + maxLength + ')');
        }
        updateCharCount();
        $textareaDesc.on('input keyup paste change', function () {
            var textLength = $(this).val() ? $(this).val().length : 0;
            if (textLength > maxLength) {
                $(this).val($(this).val().substring(0, maxLength));
                textLength = maxLength;
            }
            $('#charCountDisplay').text('(' + textLength + '/' + maxLength + ')');
        });
    }

    // Selects
    select_operation_type.select2({theme: "bootstrap4", language: 'es'});
    select_correction_concept.select2({theme: "bootstrap4", language: 'es'});
    select_paymentmethod.select2({theme: "bootstrap4", language: 'es'});
    select_transfermethods.select2({theme: "bootstrap4", language: 'es'});
    select_transfermethods.parent().hide();

    select_client.select2({
        theme: "bootstrap4",
        language: 'es',
        allowClear: true,
        ajax: {
            delay: 250,
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            url: pathname,
            data: function (params) {
                return {term: params.term, action: 'search_client'};
            },
            processResults: function (data) {
                return {results: data};
            },
        },
        placeholder: 'Ingrese un nombre o número de cedula de un cliente',
        minimumInputLength: 1,
    })
        .on('select2:select', function (e) {
            var data = e.params.data;
            $('#client_email').val(data.email || '');
        })
        .on('select2:unselect', function (e) {
            $('#client_email').val('');
        });

    $('.btnAddClient').on('click', function () {
        $('#myModalClient').modal('show');
    });

    $('#myModalClient').on('hidden.bs.modal', function (event) {
        $('#frmClient')[0].reset();
    });

    $('#frmClient').on('submit', function (e) {
        e.preventDefault();
        var form = $(this)[0];
        var params = new FormData(form);
        params.append('action', 'create_client');
        var args = {
            'params': params,
            'success': function (request) {
                select_client.select2('trigger', 'select', {data: request});
                $('#myModalClient').modal('hide');
            }
        };
        submit_with_formdata(args);
    });

    // Referencias / mixto
    const nequiGroup = $('input[name="nequi_value"]').closest('.col');
    const daviplataGroup = $('input[name="daviplata_value"]').closest('.col');
    nequiGroup.hide();
    daviplataGroup.hide();

    function toggleMixtoFields(show) {
        if (show) {
            nequiGroup.show();
            daviplataGroup.show();
        } else {
            nequiGroup.hide();
            daviplataGroup.hide();
        }
    }

    select_paymentmethod.on('change', function () {
        const selectedValue = $(this).val();
        select_transfermethods.empty();
        if (selectedValue === 'transfer') {
            select_transfermethods.append('<option value="nequi">Nequi</option>');
            select_transfermethods.append('<option value="daviplata">Daviplata</option>');
            select_transfermethods.parent().show();
            toggleMixtoFields(false);
        } else if (selectedValue === 'mixto') {
            select_transfermethods.append('<option value="mixto1">Nequi + Efectivo</option>');
            select_transfermethods.append('<option value="mixto2">Daviplata + Efectivo</option>');
            select_transfermethods.append('<option value="mixto3">Nequi + Daviplata</option>');
            select_transfermethods.parent().show();
            toggleMixtoFields(true);
        } else {
            select_transfermethods.parent().hide();
            toggleMixtoFields(false);
        }
    });

    // Tipo de operación / motivo
    select_operation_type.on('change', toggleOperationTypeSections);
    select_correction_concept.on('change', refreshItemsLockState);
    toggleOperationTypeSections();

    // Precarga el método de pago con el que quedó registrada la factura
    // referenciada, para no tener que volver a digitarlo en la nota crédito.
    // La nota crédito siempre se registra de contado (sin tipo de pago ni
    // fecha de vencimiento), por eso solo se precarga el método de pago.
    function prefillPaymentInfo(sale) {
        if (sale.paymentmethod && sale.paymentmethod.id) {
            select_paymentmethod.val(sale.paymentmethod.id).trigger('change');
        }
        if (sale.transfermethods && sale.transfermethods.id) {
            select_transfermethods.val(sale.transfermethods.id).trigger('change');
        }
        if (sale.nequi_value) {
            input_nequi_value.val(sale.nequi_value);
        }
        if (sale.daviplata_value) {
            input_daviplata_value.val(sale.daviplata_value);
        }
    }

    // Buscar factura (con referencia)
    function searchInvoiceByNumber(billNumber) {
        billNumber = (billNumber || input_reference_bill_number.val()).trim();
        if (!billNumber) {
            return message_error('Ingrese el número de la factura a buscar');
        }
        $.ajax({
            url: pathname,
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            data: {action: 'search_invoice', bill_number: billNumber},
            dataType: 'json',
            success: function (response) {
                if (response.error) {
                    return message_error(response.error);
                }
                input_reference_bill_number.val(response.factus_invoice_id || billNumber);
                lastInvoiceSearchResponse = response;
                input_reference_cufe.val(response.factus_cufe || '');

                var clientData = response.client;
                var clientText = clientData.text || (clientData.names || '');
                var option = new Option(clientText, clientData.id, true, true);
                select_client.append(option).trigger('change');
                $('#client_email').val(clientData.email || '');

                prefillPaymentInfo(response);

                refreshItemsLockState();
                if (!isAnulacion()) {
                    creditNote.setProducts(response.details.map(flattenSaleDetail), true);
                }
                toastr.success('Factura encontrada, se cargaron sus datos', '', {
                    timeOut: 3000,
                    extendedTimeOut: 1000
                });
            },
            error: function () {
                message_error('Ocurrió un error al buscar la factura');
            }
        });
    }

    $('#btnSearchInvoice').on('click', function () {
        searchInvoiceByNumber();
    });

    // Previsualización de las últimas facturas creadas: al enfocar el campo
    // (sin escribir nada) muestra las 10 más recientes para agilizar la
    // selección; al escribir, filtra (incluso solo por el consecutivo).
    input_reference_bill_number.autocomplete({
        source: function (request, response) {
            $.ajax({
                url: pathname,
                type: 'POST',
                headers: {'X-CSRFToken': csrftoken},
                data: {action: 'search_recent_invoices', term: request.term},
                dataType: 'json',
                success: function (data) {
                    response(data);
                }
            });
        },
        minLength: 0,
        delay: 200,
        select: function (event, ui) {
            event.preventDefault();
            input_reference_bill_number.val(ui.item.value);
            searchInvoiceByNumber(ui.item.value);
        }
    }).on('focus click', function () {
        $(this).autocomplete('search', $(this).val());
    });

    // Products (solo sin referencia)
    input_search_product.autocomplete({
        source: function (request, response) {
            $.ajax({
                url: pathname,
                data: {
                    'action': 'search_products',
                    'term': request.term,
                    'ids': JSON.stringify(creditNote.getProductIds()),
                },
                dataType: "json",
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                success: function (data) {
                    response(data);
                }
            });
        },
        min_length: 3,
        delay: 300,
        select: function (event, ui) {
            event.preventDefault();
            $(this).blur();
            ui.item.cant = 1;
            creditNote.addProduct(ui.item);
            $(this).val('').focus();
        }
    });

    $('#tblProducts tbody')
        .off()
        .on('change keyup', 'input[name="cant"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var cant = parseInt($(this).val());
            creditNote.detail.products[tr.row].cant = isNaN(cant) ? 0 : cant;
            creditNote.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + creditNote.detail.products[tr.row].total.toLocaleString('es-CL'));
        })
        .on('change keyup', 'input[name="dscto_unitary"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var dscto = parseFloat($(this).val());
            creditNote.detail.products[tr.row].dscto = isNaN(dscto) ? 0 : dscto;
            creditNote.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + creditNote.detail.products[tr.row].total.toLocaleString('es-CL'));
        })
        .on('change keyup', 'input[name="pvp"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var pvp = parseFloat($(this).val());
            creditNote.detail.products[tr.row].pvp = isNaN(pvp) ? 0 : pvp;
            creditNote.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + creditNote.detail.products[tr.row].total.toLocaleString('es-CL'));
        })
        .on('click', 'a[rel="remove"]', function () {
            if (!creditNote.itemsEditable) return false;
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            creditNote.detail.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
            creditNote.calculateInvoice();
        });

    // Fechas
    input_date_joined.datetimepicker({useCurrent: false, format: 'YYYY-MM-DD', locale: 'es', keepOpen: false});
    billing_period_start_date.datetimepicker({useCurrent: false, format: 'YYYY-MM-DD', locale: 'es', keepOpen: false});
    billing_period_end_date.datetimepicker({useCurrent: false, format: 'YYYY-MM-DD', locale: 'es', keepOpen: false});

    toastr.options = {
        "closeButton": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "timeOut": "0",
        "extendedTimeOut": "0"
    };

    $('#frmForm').on('submit', function (e) {
        e.preventDefault();
        if (creditNote.detail.products.length === 0) {
            return message_error('Debe tener al menos 1 producto o servicio en su detalle');
        }
        if (isWithReference() && !input_reference_bill_number.val().trim()) {
            return message_error('Debe buscar y seleccionar la factura a referenciar');
        }
        if (!isWithReference()) {
            if (!select_client.val()) {
                return message_error('Debe seleccionar un cliente');
            }
            if (!billing_period_start_date.val() || !billing_period_end_date.val()) {
                return message_error('Debe indicar el periodo de facturación de la nota crédito');
            }
        }
        var form = $(this)[0];
        var params = new FormData(form);
        params.append('products', JSON.stringify(creditNote.detail.products));

        var url_refresh = $(this).attr('data-url');
        var args = {
            'params': params,
            'success': function (request) {
                if (request.warnings) {
                    request.warnings.forEach(function (warning) {
                        toastr.warning(warning);
                    });
                }
                dialog_action({
                    'content': '¿Desea imprimir la nota crédito?',
                    'success': function () {
                        var iframe = document.getElementById('print_frame');
                        iframe.src = request.print_url;
                        iframe.onload = function () {
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();
                            iframe.contentWindow.onafterprint = function () {
                                toastr.success('La nota crédito se guardó exitosamente');
                                setTimeout(function () {
                                    location.href = url_refresh;
                                }, 1000);
                            };
                        };
                    },
                    'cancel': function () {
                        toastr.success('La nota crédito se guardó exitosamente');
                        setTimeout(function () {
                            location.href = url_refresh;
                        }, 1000);
                    }
                });
            }
        };
        submit_with_formdata(args);
    });
});
