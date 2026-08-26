var select_client;
var select_paymentmethod;
var select_transfermethods;
var select_service_type;
var select_typemethods;
var tblProducts, tblSearchProducts;
var expiration_date;
var input_search_product, input_birthdate, input_date_joined, input_cash, input_change;
var input_propina, input_nequi_value, input_daviplata_value;

// Variables globales para el manejo de múltiples PDFs
var pdfDataTransfer = new DataTransfer();
var selectedPdfUrls = [];
var activePdfIndex = -1;

var sale = {
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
        
        var dscto_global = parseFloat($('input[name="dscto"]').val());
        this.detail.dscto = isNaN(dscto_global) ? 0.00 : dscto_global;

        var globalDiscountRate = this.detail.dscto / 100;
        this.detail.total_dscto = this.detail.subtotal * globalDiscountRate;
        this.detail.total_iva = this.detail.products.filter(value => value.with_tax).reduce((a, b) => a + (b.total_iva || 0), 0) * (1 - globalDiscountRate);
        this.detail.subtotal_12_sin_iva = this.detail.subtotal_12 * (1 - globalDiscountRate);
        this.detail.total = (this.detail.subtotal - this.detail.total_dscto) + this.detail.total_iva;

        $('input[name="subtotal_0"]').val(this.detail.subtotal_0.toFixed(2));
        $('input[name="subtotal_12"]').val(this.detail.subtotal_12.toFixed(2));
        $('input[name="subtotal_12_sin_iva"]').val(this.detail.subtotal_12_sin_iva.toLocaleString('es-CL'));
        $('input[name="iva"]').val(this.detail.iva.toLocaleString('es-CL'));
        $('input[name="total_iva"]').val(this.detail.total_iva.toLocaleString('es-CL'));
        $('input[name="total_dscto"]').val(this.detail.total_dscto.toLocaleString('es-CL'));
        $('input[name="total"]').val(this.detail.total.toLocaleString('es-CL')); 

        var cash = parseFloat(input_cash.val()) || 0;
        var change = cash - sale.detail.total;
        input_change.val(change.toFixed(2));
    },
    addProduct: function (item) {
        if (!item.dscto) item.dscto = 0;
        this.detail.products.push(item);
        this.listProducts();
    },
    getProductIds: function () {
        return this.detail.products.map(value => value.id);
    },
    listProducts: function () {
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
                        return '<input type="number" step="1" min="1" class="form-control text-center" autocomplete="off" name="cant" value="' + row.cant + '">';
                    }
                },
                {
                    targets: [3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var valDscto = row.dscto !== undefined ? row.dscto : 0;
                        return '<input type="number" step="0.01" min="0" max="100" class="form-control text-center" autocomplete="off" name="dscto_unitary" value="' + valDscto + '">';
                    }
                },
                {
                    targets: [4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="number" step="0.01" min="0" class="form-control text-center" autocomplete="off" name="pvp" value="' + row.pvp + '">';
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

$(function () {
    // --- LLENADO DINÁMICO DE FACTURACIÓN ELECTRÓNICA (FACTUS) ---
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
    input_cash = $('input[name="cash"]');
    input_change = $('input[name="change"]');
    input_search_product = $('input[name="search_product"]');
    input_birthdate = $('input[name="birthdate"]');
    input_date_joined = $('input[name="date_joined"]');
    select_paymentmethod = $('select[name="paymentmethod"]');
    select_transfermethods = $('select[name="transfermethods"]');
    select_service_type = $('select[name="service_type"]');
    select_typemethods = $('select[name="typemethods"]');
    expiration_date = $('input[name="expiration_date"]');
    input_propina = $('input[name="propina"]');
    input_nequi_value = $('input[name="nequi_value"]');
    input_daviplata_value = $('input[name="daviplata_value"]');

    // Asegurar enctype en el formulario principal para soportar archivos
    var $form = $('#form-file-multi').closest('form');
    if ($form.length === 0) $form = $('form');
    $form.attr('enctype', 'multipart/form-data');

    // Escucha para la selección de archivos PDF múltiples
    $('#form-file-multi').on('change', function() {
        handlePdfFilesSelect(this.files);
    });

    // --- CONTADOR DE CARACTERES EN TIEMPO REAL (Posicionado a la derecha automáticamente) ---
    var maxLength = 500;
    var $textareaDesc = $('textarea[name="description"], #id_description');
    
    if ($textareaDesc.length) {
        $textareaDesc.attr('maxlength', maxLength);

        // Buscar el label asociado al campo de descripción para colocar el contador a la derecha
        var $formGroup = $textareaDesc.closest('.form-group');
        var $label = $formGroup.find('label').first();
        
        if ($label.length) {
            // Asegurar que el label ocupe todo el ancho con flex para empujar el contador a la derecha
            $label.css({
                'display': 'flex',
                'justify-content': 'space-between',
                'align-items': 'center',
                'width': '100%'
            });
            
            // Si el span no está dentro del label, lo movemos dentro para que la alineación flex lo mande a la esquina derecha
            var $counter = $('#charCountDisplay');
            if ($counter.length && $counter.parent()[0] !== $label[0]) {
                $counter.detach().appendTo($label);
            }
        } else {
            // Plan de respaldo si no encuentra label: flotarlo a la derecha justo encima del textarea
            $('#charCountDisplay').css({
                'float': 'right',
                'display': 'block',
                'margin-bottom': '2px'
            });
        }

        function updateCharCount() {
            var textLength = $textareaDesc.val() ? $textareaDesc.val().length : 0;
            $('#charCountDisplay').text('(' + textLength + '/' + maxLength + ')');
        }

        updateCharCount();

        $textareaDesc.on('input keyup paste change', function() {
            var textLength = $(this).val() ? $(this).val().length : 0;
            if (textLength > maxLength) {
                $(this).val($(this).val().substring(0, maxLength));
                textLength = maxLength;
            }
            $('#charCountDisplay').text('(' + textLength + '/' + maxLength + ')');
        });
    }

    // Animación de iconos para el Collapse del Card de PDFs
    $('#cardPdfSection').on('expanded.lte.cardwidget', function () {
        $('#pdfChevron').removeClass('fa-plus').addClass('fa-minus');
    });
    $('#cardPdfSection').on('collapsed.lte.cardwidget', function () {
        $('#pdfChevron').removeClass('fa-minus').addClass('fa-plus');
    });

    // Client

    $('select[name="gender"]').select2({
        language: 'es',
        theme: 'bootstrap4',
        dropdownParent: $('#myModalClient')
    });

    $('select[name="paymentmethod"]').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    $('select[name="transfermethods"]').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    $('select[name="typemethods"]').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    input_birthdate.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
        maxDate: new Date()
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

    // Referencias
    const nequiGroup = $('input[name="nequi_value"]').closest('.col');
    const daviplataGroup = $('input[name="daviplata_value"]').closest('.col');
    nequiGroup.hide();
    daviplataGroup.hide();

    // Helper
    function toggleMixtoFields(show) {
        if (show) {
            nequiGroup.show();
            daviplataGroup.show();
        } else {
            nequiGroup.hide();
            daviplataGroup.hide();
        }
    }
    
    select_paymentmethod.on('change', function(){
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

        // Si la forma de pago es transferencia o tarjeta, llenar cash con el total
        if (['transfer', 'debitCard', 'creditCard', 'mixto'].includes(selectedValue)) {
            var totalStr = $('input[name="total"]').val();
            totalStr = totalStr.replace(/\./g, '').replace(',', '.');
            var total = parseFloat(totalStr) || 0;
            input_cash.val(total).trigger('change');
        } else {
            input_cash.val('0.00').trigger('change');
        }
    });

    expiration_date.parent().hide(); 

    const templatesElement = document.getElementById('observation-templates-data');
    const templates = templatesElement ? JSON.parse(templatesElement.textContent) : {};
    const $description = $('#id_description');

    function getFutureDate() {
        let date = new Date();
        date.setDate(date.getDate() + 15);
        let year = date.getFullYear();
        let month = String(date.getMonth() + 1).padStart(2, '0');
        let day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    select_typemethods.on('change', function(){
        const selectedValue = $(this).val();
        if (selectedValue === 'credit') {
            expiration_date.parent().show();
            expiration_date.attr('required', true);
            input_cash.val('0').trigger('change');
            input_change.val('0').trigger('change');

            if (!expiration_date.val()) {
                expiration_date.val(getFutureDate());
            }
            
            if (templates['credito'] && (!$description.val() || $description.val() === templates['contado'])) {
                $description.val(templates['credito']);
            }
        } else {
            expiration_date.parent().hide();
            expiration_date.prop('required', false).val('');

            if (templates['contado'] && (!$description.val() || $description.val() === templates['credito'])) {
                $description.val(templates['contado']);
            }
        }
    }); 
    select_typemethods.trigger('change');
    
    select_service_type.on('change', function(){
        const selectedValue = $(this).val();

        if (['delivery'].includes(selectedValue)) {
            var totalStr = $('input[name="total"]').val();
            totalStr = totalStr.replace(/\./g, '').replace(',', '.');
            var total = parseFloat(totalStr) || 0;
            input_cash.val(total).trigger('change');
        } else {
            input_cash.val('0.00').trigger('change');
        }
    });

    select_service_type.trigger('change');

    select_client.select2({
        theme: "bootstrap4",
        language: 'es',
        allowClear: true,
        ajax: {
            delay: 250,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            url: pathname,
            data: function (params) {
                return {
                    term: params.term,
                    action: 'search_client'
                };
            },
            processResults: function (data) {
                return {
                    results: data
                };
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
        input_birthdate.datetimepicker('date', new Date());
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

    $('input[name="names"]')
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'letters'});
        });

    $('input[name="dni"]')
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'numbers'});
        });

    $('input[name="mobile"]')
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'numbers'});
        });

    // Products

    input_search_product.autocomplete({
        source: function (request, response) {
            $.ajax({
                url: pathname,
                data: {
                    'action': 'search_products',
                    'term': request.term,
                    'ids': JSON.stringify(sale.getProductIds()),
                },
                dataType: "json",
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                beforeSend: function () {

                },
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
            if (ui.item.stock === 0 && !ui.item.is_service) {
                message_error('El stock de este producto esta en 0');
                return false;
            }
            ui.item.cant = 1;
            sale.addProduct(ui.item);
            $(this).val('').focus();
        }
    });

    $('.btnClearProducts').on('click', function () {
        input_search_product.val('').focus();
    });

    $('.btnSearchProducts').on('click', function () {
        tblSearchProducts = $('#tblSearchProducts').DataTable({
            autoWidth: false,
            destroy: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'action': 'search_products',
                    'term': input_search_product.val(),
                    'ids': JSON.stringify(sale.getProductIds()),
                },
                dataSrc: ""
            },
            columns: [
                {data: "code"},
                {data: "short_name"},
                {data: "pvp"},
                {data: "stock"},
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
                        if (!row.is_service) {
                            return data;
                        }
                        return '---';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="add" class="btn btn-success btn-sm"><i class="fas fa-plus"></i></a>';
                    }
                }
            ],
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {

            }
        });
        $('#myModalSearchProducts').modal('show');
    });

    $('.btnRemoveAllProducts').on('click', function () {
        if (sale.detail.products.length === 0) return false;
        dialog_action({
            'content': '¿Estas seguro de eliminar todos los items de tu detalle?',
            'success': function () {
                sale.detail.products = [];
                sale.listProducts();
            },
            'cancel': function () {

            }
        });
    });

    $('#tblSearchProducts tbody')
        .off()
        .on('click', 'a[rel="add"]', function () {
            var tr = tblSearchProducts.cell($(this).closest('td, li')).index();
            var row = tblSearchProducts.row(tr.row).data();
            row.cant = 1;
            sale.addProduct(row);
            tblSearchProducts.row(tr.row).remove().draw();
        });

    // Detail products (Actualizaciones dinámicas de la tabla)

    $('#tblProducts tbody')
        .off()
        .on('change keyup', 'input[name="cant"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var cant = parseInt($(this).val());
            sale.detail.products[tr.row].cant = isNaN(cant) ? 0 : cant;
            sale.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + sale.detail.products[tr.row].total.toLocaleString('es-CL'));
        })
        .on('change keyup', 'input[name="dscto_unitary"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var dscto = parseFloat($(this).val());
            sale.detail.products[tr.row].dscto = isNaN(dscto) ? 0 : dscto;
            sale.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + sale.detail.products[tr.row].total.toLocaleString('es-CL'));
        })
        .on('change keyup', 'input[name="pvp"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var pvp = parseFloat($(this).val());
            sale.detail.products[tr.row].pvp = isNaN(pvp) ? 0 : pvp;
            sale.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + sale.detail.products[tr.row].total.toLocaleString('es-CL'));
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            sale.detail.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
            sale.calculateInvoice();
        });

    // Form

    $('input[name="dscto"]')
        .TouchSpin({
            min: 0.00,
            max: 100,
            step: 0.01,
            decimals: 2,
            boustat: 5,
            maxboostedstep: 10,
        })
        .on('change touchspin.on.min touchspin.on.max', function () {
            var dscto = $(this).val();
            if (!dscto) $(this).val('0.00');
            sale.calculateInvoice();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    input_cash
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boustat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            sale.calculateInvoice();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    input_date_joined.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
    });

    expiration_date.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
    });

    input_propina
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boustat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            sale.calculateInvoice();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    input_nequi_value
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boustat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            sale.calculateInvoice();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    input_daviplata_value
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boustat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            sale.calculateInvoice();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    // Configuración global de Toastr
    toastr.options = {
        "closeButton": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "timeOut": "0",
        "extendedTimeOut": "0"
    };
    
    $('#frmForm').on('submit', function (e) {
        e.preventDefault();
        if (sale.detail.products.length === 0) {
            return message_error('Debe tener al menos 1 producto en su detalle');
        }
        if (parseFloat(input_change.val()) < 0.00) {
            return message_error('El efectivo debe ser mayor o igual al total de la venta');
        }
        if (select_typemethods.val() === 'credit') {
            var dueDate = expiration_date.val();
            var today = new Date();
            today.setHours(0, 0, 0, 0);
            if (!dueDate || new Date(dueDate + 'T00:00:00') <= today) {
                return message_error('Para pagos a crédito, la fecha de vencimiento debe ser posterior a hoy');
            }
        }
        var form = $(this)[0];
        var params = new FormData(form);
        params.append('products', JSON.stringify(sale.detail.products));

        // Sincronizar DataTransfer al input del DOM por seguridad
        var fileInputDom = document.getElementById('form-file-multi');
        if (fileInputDom && pdfDataTransfer.files.length > 0) {
            fileInputDom.files = pdfDataTransfer.files;
        }

        // Asegurar el envío usando 'pdf_files'
        if (pdfDataTransfer.files && pdfDataTransfer.files.length > 0) {
            params.delete('pdf_files'); // Limpiamos para evitar duplicados
            for (var i = 0; i < pdfDataTransfer.files.length; i++) {
                params.append('pdf_files', pdfDataTransfer.files[i]); 
            }
        }
        var url_refresh = $(this).attr('data-url');
        var args = {
            'params': params,
            'success': function (request) {
                dialog_action({
                    'content': '¿Desea imprimir la boleta de venta?',
                    'success': function () {
                        var iframe = document.getElementById('print_frame');
                        iframe.src = request.print_url;
                        iframe.onload = function() {
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();

                            iframe.contentWindow.onafterprint = function() {
                                toastr.success('La factura se guardó exitosamente');
                                setTimeout(function() {
                                    location.href = url_refresh;
                                }, 1000);
                            };
                        };
                    },
                    'cancel': function () {
                        toastr.success('La factura se guardó exitosamente');
                        setTimeout(function() {
                            location.href = url_refresh;
                        }, 1000);
                    }
                });
            }
        };
        submit_with_formdata(args);
    });
});

// --- FUNCIONES PARA LA GESTIÓN DE ARCHIVOS PDF MÚLTIPLES ---

function handlePdfFilesSelect(files) {
    if (!files || files.length === 0) return;

    var addedAny = false;
    for (var i = 0; i < files.length; i++) {
        var file = files[i];

        if (file.type === "application/pdf" || file.name.toLowerCase().endsWith('.pdf')) {
            pdfDataTransfer.items.add(file);
            addedAny = true;
        } else {
            if (typeof toastr !== 'undefined') {
                toastr.error('El archivo "' + file.name + '" no es un documento PDF válido.');
            }
        }
    }

    if (addedAny) {
        syncPdfInputAndUI();
        selectPdfFile(pdfDataTransfer.files.length - 1);
    }
}

function syncPdfInputAndUI() {
    var input = document.getElementById('form-file-multi');
    if (input) input.files = pdfDataTransfer.files;

    var totalFiles = pdfDataTransfer.files.length;
    var $list = $('#pdfFileList');

    selectedPdfUrls.forEach(function(url) {
        if (url) URL.revokeObjectURL(url);
    });
    selectedPdfUrls = [];
    $list.empty();

    if (totalFiles > 0) {
        $('#pdfMainContainer').removeClass('d-none');
        $('#pdfCountBadge')
            .removeClass('badge-secondary')
            .addClass('badge-success')
            .text(totalFiles + (totalFiles === 1 ? ' archivo' : ' archivos'));

        for (var index = 0; index < totalFiles; index++) {
            var file = pdfDataTransfer.files[index];
            var blobUrl = URL.createObjectURL(file);
            selectedPdfUrls.push(blobUrl);
            var fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);

            var itemHtml = `
                <li class="list-group-item p-2 ${index === activePdfIndex ? 'active' : ''}" 
                    onclick="selectPdfFile(${index})" style="cursor: pointer;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="text-truncate mr-2 me-2" style="max-width: 85%;">
                            <i class="fas fa-file-pdf mr-1 me-1"></i>
                            <span class="font-weight-bold">${file.name}</span>
                            <small class="d-block text-muted">${fileSizeMB} MB</small>
                        </div>
                        <button type="button" class="btn btn-outline-danger btn-sm border-0" 
                                onclick="removePdfFile(event, ${index})" title="Quitar este PDF">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </li>
            `;
            $list.append(itemHtml);
        }
    } else {
        $('#pdfMainContainer').addClass('d-none');
        $('#pdfEmbed').attr('src', '');
        $('#pdfActiveTitle').text('Selecciona un archivo para previsualizar');
        $('#pdfActiveSize').text('');
   
        activePdfIndex = -1;
    }
}

function selectPdfFile(index) {
    if (index >= 0 && index < pdfDataTransfer.files.length) {
        activePdfIndex = index;
        var file = pdfDataTransfer.files[index];

        $('#pdfEmbed').attr('src', selectedPdfUrls[index]);
        $('#pdfActiveTitle').text(file.name);
        $('#pdfActiveSize').text((file.size / (1024 * 1024)).toFixed(2) + ' MB');

        $('#pdfFileList .list-group-item').removeClass('active');
        $('#pdfFileList .list-group-item').eq(index).addClass('active');
    }
}

function removePdfFile(event, indexToRemove) {
    if (event) event.stopPropagation();

    var newDt = new DataTransfer();
    for (var i = 0; i < pdfDataTransfer.files.length; i++) {
        if (i !== indexToRemove) {
            newDt.items.add(pdfDataTransfer.files[i]);
        }
    }
    pdfDataTransfer = newDt;

    if (activePdfIndex === indexToRemove) {
        activePdfIndex = pdfDataTransfer.files.length - 1;
    } else if (activePdfIndex > indexToRemove) {
        activePdfIndex--;
    }

    syncPdfInputAndUI();
    if (pdfDataTransfer.files.length > 0) {
        selectPdfFile(activePdfIndex >= 0 ? activePdfIndex : 0);
    }
}

function clearAllPdfs(event) {
    if (event) event.stopPropagation();
    pdfDataTransfer = new DataTransfer();
    activePdfIndex = -1;
    var input = document.getElementById('form-file-multi');
    if (input) input.value = '';
    syncPdfInputAndUI();
}


// --- ACCIÓN DE PREVISUALIZACIÓN DE FACTURA (ESTILO FACTUS / BOOTSTRAP 5) ---
    $('#btnPreviewInvoice').on('click', function (e) {
        e.preventDefault();

        if (sale.detail.products.length === 0) {
            return message_error('Debe tener al menos 1 producto en su detalle para previsualizar');
        }

        // Obtener datos del formulario
        const dateJoined = $('input[name="date_joined"]').val() || '03-08-2026 11:53:57 AM';
        const numberingRange = $('input[name="numbering_range"]').val() || 'SETP990000005';
        const consecutive = $('input[name="consecutive"]').val() || '5';
        
        // Cliente
        const clientText = select_client.find('option:selected').text() || 'COORSERPARK SAS';
        const clientEmail = $('#client_email').val() || 'prueba1@gmail.com';
        
        // Pagos y observaciones
        const paymentMethod = $('select[name="paymentmethod"] option:selected').text() || 'Pago a crédito';
        const typeMethods = $('select[name="typemethods"] option:selected').text() || 'Consignación';
        const description = $('textarea[name="description"], #id_description').val() || 'Factura generada desde POS';
        const expirationDate = $('input[name="expiration_date"]').val() || '18-08-2026';

        // Totales calculados
        const subtotalSinIva = $('input[name="subtotal_12_sin_iva"]').val() || '0.00';
        const totalIva = $('input[name="total_iva"]').val() || '0.00';
        const totalDscto = $('input[name="total_dscto"]').val() || '0.00';
        const totalGeneral = $('input[name="total"]').val() || '0.00';

        // Construir filas de productos para la tabla
        let productsHtml = '';
        let totalLines = sale.detail.products.length;
        
        sale.detail.products.forEach(function (item, index) {
            let pvp = parseFloat(item.pvp) || 0;
            let cant = parseFloat(item.cant) || 0;
            let dscto = parseFloat(item.dscto) || 0;
            let itemTotal = item.total || 0;
            let taxRate = item.iva || '0.00';

            productsHtml += `
                <tr>
                    <td class="text-center align-middle">${index + 1}</td>
                    <td class="text-start align-middle"><code>${item.code || '15'}</code></td>
                    <td class="text-start align-middle">${item.name || item.short_name || 'Servicio'}</td>
                    <td class="text-end align-middle">$${pvp.toLocaleString('es-CL', {minimumFractionDigits: 2})}</td>
                    <td class="text-center align-middle">${cant.toFixed(2)}</td>
                    <td class="text-end align-middle">$${dscto.toLocaleString('es-CL', {minimumFractionDigits: 2})}</td>
                    <td class="text-center align-middle"><small class="fw-bold">(IVA)</small> ${taxRate}%</td>
                    <td class="text-end align-middle fw-bold">$${parseFloat(itemTotal).toLocaleString('es-CL', {minimumFractionDigits: 2})}</td>
                </tr>
            `;
        });

        // Obtener la ruta del logo de la empresa y asegurar que sea absoluta desde la raíz
        let companyLogo = 'https://cdn-sandbox.factus.com.co/companies/900438757/logos/logo-1L9qH3MCQcObTV27z4h2xMJKx5sIiSI6.png'; // Respaldo por defecto
        
        if (typeof company !== 'undefined' && company.image) {
            // Si la ruta no empieza con http ni con barra, le anteponemos la barra '/' para que sea absoluta desde el dominio
            companyLogo = company.image.startsWith('http') ? company.image : '/' + company.image.replace(/^\/+/, '');
        }

        // Maquetación HTML utilizando estrictamente Bootstrap 5 (Tamaño de fuente incrementado a 0.95rem)
        const previewHtml = `
            <div class="container-fluid bg-white p-4 border rounded shadow-sm text-dark" style="font-size: 0.95rem;">
                
                <!-- ENCABEZADO -->
                <div class="row align-items-center pb-3 mb-4 border-bottom">
                    <div class="col-4 text-center">
                        <img src="${companyLogo}" class="img-fluid" style="max-width: 140px;" alt="Logo de la empresa">
                    </div>
                    <div class="col-4 text-center">
                        <h6 class="fw-bold text-uppercase mb-1">Factura electrónica de Venta</h6>
                        <h5 class="fw-bold text-primary mb-2">${numberingRange}</h5>
                        <p class="fw-bold mb-1">EXEQUIALES ESCOBAR S.A.S</p>
                        <p class="mb-0 text-muted small">NIT 900438757 - 2</p>
                        <p class="mb-0 text-muted small">3023812461 | fexequialesescobar@hotmail.com</p>
                        <p class="mb-0 text-muted small">Calle 5 # 7A-31, Facatativá - Cundinamarca</p>
                    </div>
                    <div class="col-4 text-end">
                        <span class="badge bg-success">Factura Electrónica</span>
                    </div>
                </div>

                <!-- DATOS CLIENTE Y FECHAS -->
                <div class="row mb-4">
                    <div class="col-lg-7 mb-3 mb-lg-0">
                        <ul class="list-group list-group-flush border rounded">
                            <li class="list-group-item d-flex py-1 px-2 bg-light"><span class="fw-bold w-25">CC/NIT:</span> <span class="w-75">12345678 - 8</span></li>
                            <li class="list-group-item d-flex py-1 px-2"><span class="fw-bold w-25">Cliente:</span> <span class="w-75">${clientText}</span></li>
                            <li class="list-group-item d-flex py-1 px-2 bg-light"><span class="fw-bold w-25">País:</span> <span class="w-75">Colombia</span></li>
                            <li class="list-group-item d-flex py-1 px-2"><span class="fw-bold w-25">Municipio:</span> <span class="w-75">Bogotá, D.C. / Bogota-D.C.</span></li>
                            <li class="list-group-item d-flex py-1 px-2 bg-light"><span class="fw-bold w-25">Dirección:</span> <span class="w-75">bogota</span></li>
                            <li class="list-group-item d-flex py-1 px-2"><span class="fw-bold w-25">Email:</span> <span class="w-75">${clientEmail}</span></li>
                        </ul>
                    </div>
                    <div class="col-lg-5">
                        <ul class="list-group list-group-flush border rounded">
                            <li class="list-group-item d-flex justify-content-between py-2 px-2 bg-light">
                                <span class="fw-bold">Fecha de generación:</span> 
                                <span>${dateJoined}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between py-2 px-2">
                                <span class="fw-bold">Fecha de validación:</span> 
                                <span>${dateJoined}</span>
                            </li>
                        </ul>
                    </div>
                </div>

                <!-- TABLA DE PRODUCTOS -->
                <div class="table-responsive mb-4">
                    <table class="table table-bordered table-sm align-middle">
                        <thead class="table-light text-center">
                            <tr>
                                <th>#</th>
                                <th>Código</th>
                                <th>Descripción</th>
                                <th>Val. Unit</th>
                                <th>Cantidad</th>
                                <th>Descuento</th>
                                <th>Impuesto %</th>
                                <th>Val. Item</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${productsHtml}
                        </tbody>
                    </table>
                </div>

                <!-- OBSERVACIONES Y TOTALES -->
                <div class="row mb-4">
                    <div class="col-lg-7 mb-3 mb-lg-0">
                        <div class="border rounded p-3 h-100 bg-light">
                            <h6 class="fw-bold text-uppercase border-bottom pb-2">Observaciones</h6>
                            <p class="mb-0 text-muted" style="white-space: pre-line;">${description}</p>
                        </div>
                    </div>
                    <div class="col-lg-5">
                        <div class="border rounded bg-white p-2">
                            <h6 class="fw-bold text-uppercase border-bottom pb-2 text-center bg-light m-0 p-2">Totales</h6>
                            <table class="table table-sm table-borderless mb-0">
                                <tr><td>Nro líneas:</td><td class="text-end">${totalLines}</td></tr>
                                <tr><td>Valor bruto:</td><td class="text-end">$${subtotalSinIva}</td></tr>
                                <tr><td>Base imponible:</td><td class="text-end">$0.00</td></tr>
                                <tr><td>Impuestos:</td><td class="text-end">$${totalIva}</td></tr>
                                <tr><td>Descuento global (-):</td><td class="text-end">$${totalDscto}</td></tr>
                                <tr><td>Recargo global (+):</td><td class="text-end">$0.00</td></tr>
                                <tr class="border-top fw-bold text-success">
                                    <td class="pt-2">Total factura:</td><td class="text-end pt-2">$${totalGeneral}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- DETALLES DE PAGO Y TIPO DE OPERACIÓN -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="fw-bold">Tipo de operación</h6>
                        <p class="text-muted mb-0">Estándar</p>
                    </div>
                    <div class="col-md-6">
                        <h6 class="fw-bold">Detalles de Pago</h6>
                        <div class="border-start border-3 border-primary ps-3 py-1">
                            <p class="mb-1"><strong>Forma de pago:</strong> ${paymentMethod}</p>
                            <p class="mb-1"><strong>Medio de pago:</strong> ${typeMethods}</p>
                            <p class="mb-1"><strong>Referencia:</strong> pago-${consecutive}</p>
                            <p class="mb-1"><strong>Monto:</strong> $${totalGeneral}</p>
                            <p class="mb-0"><strong>Fecha de vencimiento:</strong> ${expirationDate}</p>
                        </div>
                    </div>
                </div>

                <!-- PIE DE PAGINA / CUFE -->
                <div class="bg-light p-3 rounded text-center border">
                    <small class="fw-bold text-break d-block mb-2">CUFE: 940700f886b73eeee9a5ae93f23372e00930f3bb68d9489a55a99030e38dcbed</small>
                    <hr class="my-2">
                    <p class="text-muted mb-0" style="font-size: 0.85rem;">
                        Actividad económica: 9603 - Resolución de Facturación Electrónica No: 18760000001 - Prefijo: SETP Rango 990000000 Al 995000000 - Vigencia desde 19-01-2019 - hasta 19-01-2030
                    </p>
                </div>

            </div>
        `;

        $('#previewInvoiceContent').html(previewHtml);
        $('#modalPreviewInvoice').modal('show');
    });