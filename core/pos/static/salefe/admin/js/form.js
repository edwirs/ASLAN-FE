var select_client;
var select_paymentmethod;
var select_transfermethods;
var select_service_type;
var select_typemethods;
var tblProducts, tblSearchProducts;
var expiration_date;
var input_search_product, input_birthdate, input_date_joined, input_cash, input_change;
var input_propina, input_nequi_value, input_daviplata_value;
var selectedClient = null;   // datos completos del cliente elegido (los usa la previsualización)

// Formato de dinero de las casillas de totales: miles con punto y hasta 2 decimales (302.800 · 1.234,5)
function fmtMoney(n) {
    return (parseFloat(n) || 0).toLocaleString('es-CO', {maximumFractionDigits: 2});
}

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

            value.iva = lineTaxRate(value);
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

        // Total bruto: precio × cantidad de todas las líneas, antes de descuentos.
        // Descuentos: los de cada línea más el global. Subtotal: bruto menos descuentos. Total: subtotal + impuestos.
        var gross = this.detail.products.reduce(function (a, b) { return a + (b.subtotal || 0); }, 0);
        var lineDiscounts = this.detail.products.reduce(function (a, b) { return a + (b.total_dscto || 0); }, 0);
        this.detail.gross = gross;
        this.detail.discounts = lineDiscounts + this.detail.total_dscto;
        this.detail.net = gross - this.detail.discounts;

        $('input[name="gross_total"]').val(fmtMoney(this.detail.gross));
        $('input[name="total_dscto"]').val(fmtMoney(this.detail.discounts));
        $('input[name="net_subtotal"]').val(fmtMoney(this.detail.net));
        $('input[name="total_iva"]').val(fmtMoney(this.detail.total_iva));
        $('input[name="total"]').val(fmtMoney(this.detail.total));

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
        selectedClient = data;
        $('#client_email').val(data.email || '');
    })
    .on('select2:unselect', function (e) {
        selectedClient = null;
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
                if (request.warnings) {
                    request.warnings.forEach(function (warning) {
                        toastr.warning(warning);
                    });
                }
                // Guardar no imprime nada: la factura se imprime después de validarla (opción del listado).
                toastr.success((typeof EDIT_MODE !== 'undefined' && EDIT_MODE)
                    ? 'Los cambios de la factura se guardaron. Recuerde validarla desde el listado para enviarla a la DIAN.'
                    : 'La factura se guardó. Recuerde validarla desde el listado para enviarla a la DIAN.');
                setTimeout(function () {
                    location.href = url_refresh;
                }, 1500);
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


// ---------------------------------------------------------------------------------------------------------
// EDICIÓN: carga en el formulario la factura que se está editando (la entrega el servidor en #edit-sale-data)
// ---------------------------------------------------------------------------------------------------------
var EDIT_MODE = !!document.getElementById('edit-sale-data');

$(function () {
    var el = document.getElementById('edit-sale-data');
    if (!el) {
        return;
    }
    var d = JSON.parse(el.textContent);

    // Cliente
    selectedClient = d.client;
    select_client.append(new Option(d.client.text, d.client.id, true, true)).trigger('change');
    $('#client_email').val(d.client.email || '');

    // Forma y medio de pago. Cada cambio reconstruye listas y reinicia valores, por eso los montos van al final.
    select_paymentmethod.val(d.paymentmethod).trigger('change');
    if (d.transfermethods) {
        select_transfermethods.val(d.transfermethods).trigger('change');
    }
    select_typemethods.val(d.typemethods).trigger('change');
    select_service_type.val(d.service_type).trigger('change');
    if (d.expiration_date) {
        expiration_date.val(d.expiration_date);
    }

    // Fecha, descuento, observaciones y productos
    $('input[name="date_joined"]').val(d.date_joined);
    $('input[name="dscto"]').val(parseFloat(d.dscto).toFixed(2));
    $('textarea[name="description"], #id_description').first().val(d.description).trigger('change');
    sale.detail.products = d.products;
    sale.listProducts();

    // Montos
    input_propina.val(parseFloat(d.propina).toFixed(2));
    input_nequi_value.val(parseFloat(d.nequi_value).toFixed(2));
    input_daviplata_value.val(parseFloat(d.daviplata_value).toFixed(2));
    input_cash.val(parseFloat(d.cash).toFixed(2)).trigger('change');
});

// ---------------------------------------------------------------------------------------------------------
// PREVISUALIZACIÓN: todo sale de la factura que se está llenando; lo que aún no existe se indica como pendiente
// ---------------------------------------------------------------------------------------------------------
function esc(v) {
    return $('<div>').text(v === null || v === undefined ? '' : String(v)).html();
}

function money(n) {
    return '$' + (parseFloat(n) || 0).toLocaleString('es-CO', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

function dmy(ymd) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ymd || '');
    return m ? m[3] + '-' + m[2] + '-' + m[1] : (ymd || '');
}

// «IVA 19%», «INC 8%», «Excluido», «Exento»: igual a lo que se enviará a Factus
function taxLabelOf(item) {
    if (!item.with_tax) {
        return item.tax === 'iva_excluido' ? 'Excluido' : (item.tax === 'iva_exento' ? 'Exento' : 'IVA 0%');
    }
    return (String(item.tax || '').indexOf('inc') === 0 ? 'INC ' : 'IVA ') + (parseFloat(item.tax_rate) || 0) + '%';
}

// Impuestos agrupados por tarifa, con el descuento global aplicado (igual que el servidor)
function previewTaxGroups(products, globalRate) {
    var groups = {};
    products.forEach(function (item) {
        if (!item.with_tax || !(item.iva > 0)) {
            return;
        }
        var label = taxLabelOf(item);
        groups[label] = groups[label] || {label: label, base: 0, tax: 0};
        groups[label].base += (item.total || 0) * (1 - globalRate);
        groups[label].tax += (item.total_iva || 0) * (1 - globalRate);
    });
    return Object.keys(groups).sort().map(function (k) { return groups[k]; });
}

function buildPreviewHtml(range) {
    var company = {};
    try { company = JSON.parse(document.getElementById('company-info-data').textContent) || {}; } catch (e) { company = {}; }
    var detail = sale.detail;
    var products = detail.products;
    var globalRate = (parseFloat(detail.dscto) || 0) / 100;
    var client = selectedClient || {};

    var isCredit = select_typemethods.val() === 'credit';
    var paymentForm = isCredit ? 'Crédito' : 'Contado';
    // El medio de pago que recibirá Factus: efectivo (10) o consignación bancaria (42)
    var paymentMethod = select_paymentmethod.val() === 'cash' ? 'Efectivo' : 'Consignación bancaria';
    var description = $('textarea[name="description"], #id_description').first().val() || '';
    var dueDate = isCredit ? dmy(expiration_date.val()) : '—';
    var reference = (typeof EDIT_MODE !== 'undefined' && EDIT_MODE)
        ? 'pago-' + JSON.parse(document.getElementById('edit-sale-data').textContent).id : 'pago-(se asigna al guardar)';

    var rows = products.map(function (item, index) {
        return '<tr>' +
            '<td class="text-center align-middle">' + (index + 1) + '</td>' +
            '<td class="text-start align-middle"><code>' + esc(item.code) + '</code></td>' +
            '<td class="text-start align-middle">' + esc(item.name || item.short_name) + '</td>' +
            '<td class="text-end align-middle">' + money(item.pvp) + '</td>' +
            '<td class="text-center align-middle">' + (parseFloat(item.cant) || 0).toFixed(2) + '</td>' +
            '<td class="text-end align-middle">' + (parseFloat(item.dscto) || 0).toFixed(2) + '%</td>' +
            '<td class="text-center align-middle"><small class="fw-bold">' + esc(taxLabelOf(item)) + '</small></td>' +
            '<td class="text-end align-middle fw-bold">' + money(item.total) + '</td>' +
            '</tr>';
    }).join('');

    var taxRows = previewTaxGroups(products, globalRate).map(function (g) {
        return '<tr><td>' + esc(g.label) + ':</td><td class="text-end">' + money(g.tax) + '</td></tr>';
    }).join('') || '<tr><td>Impuestos:</td><td class="text-end">' + money(0) + '</td></tr>';

    // «current» es el PRÓXIMO número del rango; el número final se confirma al validar
    var numbering = range
        ? esc((range.prefix || '') + range.current) + '<br><small class="text-muted fw-normal">próxima numeración · se confirma al validar</small>'
        : 'Se asigna al validar en la DIAN';
    var resolution = range
        ? 'Resolución de facturación electrónica No: ' + esc(range.resolution_number) + ' - Prefijo: ' + esc(range.prefix || '') +
          ' - Rango ' + esc(range.from) + ' al ' + esc(range.to) + (range.date_from ? ' - Vigencia desde ' + esc(dmy(range.date_from)) + ' hasta ' + esc(dmy(range.date_to)) : '')
        : 'La resolución y el rango de numeración se aplican al validar la factura.';

    var logo = company.logo
        ? '<img src="' + esc(company.logo) + '" class="img-fluid" style="max-width: 140px;" alt="Logo de la empresa">'
        : '<i class="fas fa-building fa-3x text-muted"></i>';
    var docType = client.document_type && client.document_type.abbreviation ? client.document_type.abbreviation : 'CC/NIT';
    var dni = client.dni ? client.dni + (client.dv ? ' - ' + client.dv : '') : '';
    var contact = [company.mobile, company.phone, company.email].filter(Boolean).join(' | ');

    function li(label, value, shaded) {
        return '<li class="list-group-item d-flex py-1 px-2' + (shaded ? ' bg-light' : '') + '"><span class="fw-bold w-25">' + label +
            '</span> <span class="w-75">' + esc(value || '—') + '</span></li>';
    }

    return '<div class="container-fluid bg-white p-4 border rounded shadow-sm text-dark" style="font-size: 0.95rem;">' +
        '<div class="row align-items-center pb-3 mb-4 border-bottom">' +
            '<div class="col-4 text-center">' + logo + '</div>' +
            '<div class="col-4 text-center">' +
                '<h6 class="fw-bold text-uppercase mb-1">Factura electrónica de Venta</h6>' +
                '<h5 class="fw-bold text-primary mb-2">' + numbering + '</h5>' +
                '<p class="fw-bold mb-1">' + esc(company.name) + '</p>' +
                '<p class="mb-0 text-muted small">NIT ' + esc(company.nit) + '</p>' +
                '<p class="mb-0 text-muted small">' + esc(contact) + '</p>' +
                '<p class="mb-0 text-muted small">' + esc(company.address) + '</p>' +
            '</div>' +
            '<div class="col-4 text-end"><span class="badge bg-warning text-dark">Borrador · sin validar</span></div>' +
        '</div>' +
        '<div class="row mb-4">' +
            '<div class="col-lg-7 mb-3 mb-lg-0"><ul class="list-group list-group-flush border rounded">' +
                li(esc(docType) + ':', dni, true) +
                li('Cliente:', client.names || client.text, false) +
                li('País:', 'Colombia', true) +
                li('Municipio:', client.municipality ? client.municipality.name : '', false) +
                li('Dirección:', client.address, true) +
                li('Email:', $('#client_email').val() || client.email, false) +
                li('Teléfono:', client.mobile, true) +
            '</ul></div>' +
            '<div class="col-lg-5"><ul class="list-group list-group-flush border rounded">' +
                '<li class="list-group-item d-flex justify-content-between py-2 px-2 bg-light"><span class="fw-bold">Fecha de generación:</span><span>' + esc(dmy($('input[name="date_joined"]').val())) + '</span></li>' +
                '<li class="list-group-item d-flex justify-content-between py-2 px-2"><span class="fw-bold">Fecha de validación:</span><span class="text-muted">Pendiente</span></li>' +
            '</ul></div>' +
        '</div>' +
        '<div class="table-responsive mb-4"><table class="table table-bordered table-sm align-middle">' +
            '<thead class="table-light text-center"><tr><th>#</th><th>Código</th><th>Descripción</th><th>Val. Unit</th><th>Cantidad</th><th>Descuento</th><th>Impuesto</th><th>Val. Item</th></tr></thead>' +
            '<tbody>' + rows + '</tbody></table></div>' +
        '<div class="row mb-4">' +
            '<div class="col-lg-7 mb-3 mb-lg-0"><div class="border rounded p-3 h-100 bg-light">' +
                '<h6 class="fw-bold text-uppercase border-bottom pb-2">Observaciones</h6>' +
                '<p class="mb-0 text-muted" style="white-space: pre-line;">' + esc(description || 'Sin observaciones') + '</p>' +
            '</div></div>' +
            '<div class="col-lg-5"><div class="border rounded bg-white p-2">' +
                '<h6 class="fw-bold text-uppercase border-bottom pb-2 text-center bg-light m-0 p-2">Totales</h6>' +
                '<table class="table table-sm table-borderless mb-0">' +
                    '<tr><td>Nro líneas:</td><td class="text-end">' + products.length + '</td></tr>' +
                    '<tr><td>Valor bruto:</td><td class="text-end">' + money(detail.gross) + '</td></tr>' +
                    '<tr><td>Base imponible:</td><td class="text-end">' + money(detail.subtotal_12_sin_iva) + '</td></tr>' +
                    taxRows +
                    '<tr><td>Descuentos (-):</td><td class="text-end">' + money(detail.discounts) + '</td></tr>' +
                    '<tr class="border-top fw-bold text-success"><td class="pt-2">Total factura:</td><td class="text-end pt-2">' + money(detail.total) + '</td></tr>' +
                '</table></div></div>' +
        '</div>' +
        '<div class="row mb-4">' +
            '<div class="col-md-6"><h6 class="fw-bold">Tipo de operación</h6><p class="text-muted mb-0">Estándar</p></div>' +
            '<div class="col-md-6"><h6 class="fw-bold">Detalles de Pago</h6>' +
                '<div class="border-start border-3 border-primary ps-3 py-1">' +
                    '<p class="mb-1"><strong>Forma de pago:</strong> ' + esc(paymentForm) + '</p>' +
                    '<p class="mb-1"><strong>Medio de pago:</strong> ' + esc(paymentMethod) + '</p>' +
                    '<p class="mb-1"><strong>Referencia:</strong> ' + esc(reference) + '</p>' +
                    '<p class="mb-1"><strong>Monto:</strong> ' + money(detail.total) + '</p>' +
                    '<p class="mb-0"><strong>Fecha de vencimiento:</strong> ' + esc(dueDate) + '</p>' +
                '</div></div>' +
        '</div>' +
        '<div class="bg-light p-3 rounded text-center border">' +
            '<small class="fw-bold text-break d-block mb-2">CUFE: se genera al validar la factura en la DIAN</small><hr class="my-2">' +
            '<p class="text-muted mb-0" style="font-size: 0.85rem;">' + resolution + '</p>' +
        '</div>' +
    '</div>';
}

// ---------------------------------------------------------------------------------------------------------
// NUMERACIÓN: rango y consecutivo que siguen en Factus (solo consulta; no reserva ni consume ningún número)
// ---------------------------------------------------------------------------------------------------------
var numberingRange;          // undefined = consultando · null = no disponible · objeto = rango activo
var numberingLoad = $.Deferred();

function showNumbering(response) {
    var range = response && response.range ? response.range : null;
    var $hint = $('#numberingHint').removeClass('text-danger text-muted');
    if (!range) {
        $('#numbering_range').val('No disponible');
        $('#consecutive').val('—');
        $hint.addClass('text-danger').text((response && response.error) ||
            'No se pudo consultar a Factus. La numeración se asigna al validar la factura.');
        return;
    }
    $('#numbering_range').val((range.prefix ? range.prefix + ' ' : '') + '(' + range.from + ' - ' + range.to + ')');
    $('#consecutive').val(range.current);
    if (range.exhausted) {
        $hint.addClass('text-danger').text('El rango de numeración se agotó: solicite uno nuevo en Factus.');
    } else {
        $hint.addClass('text-muted').text('Próxima factura: ' + (range.prefix || '') + range.current + '. Se confirma al validar la factura (opción «Validar» del listado).');
    }
}

$(function () {
    $.ajax({
        url: pathname, type: 'POST', dataType: 'json', timeout: 12000,
        headers: {'X-CSRFToken': csrftoken},
        data: {action: 'numbering_preview'},
        success: function (response) {
            numberingRange = response && response.range ? response.range : null;
            showNumbering(response);
            numberingLoad.resolve();
        },
        error: function () {
            numberingRange = null;
            showNumbering(null);
            numberingLoad.resolve();
        }
    });
});

$(function () {
    $('#btnPreviewInvoice').on('click', function (e) {
        e.preventDefault();
        if (sale.detail.products.length === 0) {
            return message_error('Debe tener al menos 1 producto en su detalle para previsualizar');
        }
        // Si la numeración todavía se está consultando, se espera a que termine (máx. 12 s); luego se muestra.
        var $btn = $(this).prop('disabled', true);
        numberingLoad.always(function () {
            $btn.prop('disabled', false);
            $('#previewInvoiceContent').html(buildPreviewHtml(numberingRange || null));
            $('#modalPreviewInvoice').modal('show');
        });
    });
});
