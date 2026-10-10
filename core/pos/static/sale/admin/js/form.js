var select_client;
var select_paymentmethod;
var select_transfermethods;
var select_service_type;
var select_typemethods;
var tblProducts, tblSearchProducts;
var expiration_date;
var input_search_product, input_birthdate, input_date_joined, input_cash, input_change;

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
            value.iva = parseFloat(tax);
            value.price_with_vat = value.pvp + (value.pvp * value.iva);
            value.subtotal = value.pvp * value.cant;
            value.total_dscto = value.subtotal * parseFloat((value.dscto / 100));
            value.total_iva = (value.subtotal - value.total_dscto) * value.iva;
            value.total = value.subtotal - value.total_dscto;
        });

        this.detail.subtotal_0 = this.detail.products.filter(value => !value.with_tax).reduce((a, b) => a + (b.total || 0), 0);
        this.detail.subtotal_12 = this.detail.products.filter(value => value.with_tax).reduce((a, b) => a + (b.total || 0), 0);
        this.detail.subtotal = parseFloat(this.detail.subtotal_0) + parseFloat(this.detail.subtotal_12);
        this.detail.dscto = parseFloat($('input[name="dscto"]').val());
        this.detail.total_dscto = this.detail.subtotal * (this.detail.dscto / 100);
        this.detail.total_iva = this.detail.products.filter(value => value.with_tax).reduce((a, b) => a + (b.total_iva || 0), 0);
        this.detail.total = this.detail.subtotal - this.detail.total_dscto;
        this.detail.subtotal_12_sin_iva = this.detail.subtotal_12 - this.detail.total_iva;

        $('input[name="subtotal_0"]').val(this.detail.subtotal_0.toFixed(2));
        $('input[name="subtotal_12"]').val(this.detail.subtotal_12.toFixed(2));
        $('input[name="subtotal_12_sin_iva"]').val(this.detail.subtotal_12_sin_iva.toLocaleString('es-CL'));
        $('input[name="iva"]').val(this.detail.iva.toLocaleString('es-CL'));
        $('input[name="total_iva"]').val(this.detail.total_iva.toLocaleString('es-CL'));
        $('input[name="total_dscto"]').val(this.detail.total_dscto.toLocaleString('es-CL'));
        $('input[name="total"]').val(this.detail.total.toLocaleString('es-CL')); 
        $('input[name="cash"]').val(this.detail.total); 

        sale.calculateChange();
    },
    calculateChange: function () {

        let total = parseFloat(sale.detail.total) || 0;
        let cash = parseFloat(input_cash.val()) || 0;
        let nequi = parseFloat(input_nequi_value.val()) || 0;
        let daviplata = parseFloat(input_daviplata_value.val()) || 0;

        let paymentMethod = select_paymentmethod.val();
        let transferMethod = select_transfermethods.val();

        let totalReceived = 0;

        // =========================
        // EFECTIVO
        // =========================
        if (paymentMethod === 'cash') {

            totalReceived = cash;
        }

        // =========================
        // TRANSFERENCIA
        // =========================
        else if (paymentMethod === 'transfer') {

            if (transferMethod === 'nequi') {

                totalReceived = nequi;
                input_cash.val(0);
            }

            else if (transferMethod === 'daviplata') {

                totalReceived = daviplata;
                input_cash.val(0);
            }
        }

        // =========================
        // MIXTO
        // =========================
        else if (paymentMethod === 'mixto') {

            // Nequi + efectivo
            if (transferMethod === 'mixto1') {

                let faltante = total - nequi;

                if (faltante < 0) {
                    faltante = 0;
                }

                input_cash.val(faltante.toFixed(2));

                totalReceived = nequi + faltante;
            }

            // Daviplata + efectivo
            else if (transferMethod === 'mixto2') {

                let faltante = total - daviplata;

                if (faltante < 0) {
                    faltante = 0;
                }

                input_cash.val(faltante.toFixed(2));

                totalReceived = daviplata + faltante;
            }

            // Nequi + Daviplata
            else if (transferMethod === 'mixto3') {

                input_cash.val(0);

                totalReceived = nequi + daviplata;
            }
        }

        // =========================
        // TARJETAS
        // =========================
        else if (
            paymentMethod === 'debitCard' ||
            paymentMethod === 'creditCard'
        ) {

            input_cash.val(total.toFixed(2));

            totalReceived = total;
        }

        // =========================
        // CAMBIO
        // =========================
        let change = totalReceived - total;

        if (change < 0) {
            change = 0;
        }

        input_change.val(change.toFixed(2));
    },
    addProduct: function (item) {
        this.detail.products.push(item);
        this.listProducts();
    },
    // --- Presentaciones (caja, six pack, variantes...) ---
    productOptions: {},
    canEditPrice: false,
    optionsFor: function (productId) {
        var options = this.productOptions[productId];
        return options && options.length > 1 ? options : null;
    },
    hasOwnStockVariants: function (productId) {
        var options = this.productOptions[productId];
        return !!(options && options.length && options[0].own_stock);
    },
    unitsInOtherLines: function (productId, exceptKey) {
        var units = 0;
        this.detail.products.forEach(function (line) {
            if (line.id === productId && line.key !== exceptKey && !line.own_stock) {
                units += line.cant * (line.factor || 1);
            }
        });
        return units;
    },
    // Cuántas unidades de esta línea caben todavía (conversión: stock compartido del producto; variantes: stock propio)
    availableQty: function (line) {
        if (line.is_service) {
            return Infinity;
        }
        var raw = line.own_stock ? line.row_stock : (line.stock - this.unitsInOtherLines(line.id, line.key)) / (line.factor || 1);
        return line.allow_decimals ? Math.floor(raw * 1000 + 1e-6) / 1000 : Math.floor(raw + 1e-9);
    },
    // Agrega el producto; si tiene presentaciones, pregunta cuál.
    pickProduct: function (item, done) {
        var options = this.optionsFor(item.id);
        if (options) {
            this.showChooser(item, options, done);
            return;
        }
        this.addLine(item, null);
        if (done) {
            done();
        }
    },
    // ¿Ya están en el detalle todas las formas de vender este producto?
    isFullyAdded: function (productId) {
        var options = this.optionsFor(productId);
        var lines = this.detail.products.filter(line => line.id === productId);
        return options ? options.every(opt => lines.some(line => line.key === productId + '-' + (opt.presentation_id || 0))) : lines.length > 0;
    },
    addLine: function (item, opt) {
        var hasOptions = !!this.optionsFor(item.id);
        opt = opt || {presentation_id: null, name: '', factor: 1, pvp: item.pvp, own_stock: false, stock: null};
        var key = item.id + '-' + (opt.presentation_id || 0);
        var unit = item.unit_name || 'unidades';
        var existing = this.detail.products.find(line => line.key === key);
        if (existing) {
            var next = Math.round((parseFloat(existing.cant) + 1) * 1000) / 1000;
            if (this.availableQty(existing) < next) {
                message_error('Stock insuficiente: solo hay ' + Math.max(this.availableQty(existing), 0).toLocaleString('es-CL', {maximumFractionDigits: 3}) + ' disponibles.');
                return;
            }
            existing.cant = next;
            this.listProducts();
            return;
        }
        var line = $.extend({}, item, {
            cant: 1,
            key: key,
            presentation_id: opt.presentation_id,
            presentation_name: hasOptions ? opt.name : '',
            factor: opt.factor,
            own_stock: !!opt.own_stock,
            row_stock: opt.own_stock ? opt.stock : null,
            has_options: hasOptions,
            pvp: opt.pvp,
            base_pvp: opt.pvp
        });
        var min = line.allow_decimals ? 0.001 : 1;
        var avail = this.availableQty(line);
        if (avail < min) {
            message_error('El stock de este producto esta en 0');
            return;
        }
        line.cant = Math.min(1, avail);
        this.addProduct(line);
    },
    showChooser: function (item, options, done) {
        var self = this;
        var list = $('#presentation_options').empty();
        // No se ofrecen las presentaciones que ya están en el detalle
        options = options.filter(opt => !self.detail.products.some(line => line.key === item.id + '-' + (opt.presentation_id || 0)));
        if (!options.length) {
            message_error('Ya agregó todas las presentaciones de este producto.');
            if (done) {
                done();
            }
            return;
        }
        var variants = !!options[0].own_stock;
        var num = value => parseFloat(value).toLocaleString('es-CL', {maximumFractionDigits: 3});
        $('#presentation_title').text(item.name);
        $('#presentation_stock').text(item.is_service ? '' : (variants ? '' : 'Stock: ' + num(item.stock) + ' ' + (item.unit_name || '')));
        options.forEach(function (opt) {
            var key = item.id + '-' + (opt.presentation_id || 0);
            var probe = {id: item.id, key: key, is_service: item.is_service, allow_decimals: item.allow_decimals,
                stock: item.stock, factor: opt.factor, own_stock: !!opt.own_stock, row_stock: opt.stock};
            var avail = self.availableQty(probe);
            var min = item.allow_decimals ? 0.001 : 1;
            var detail;
            if (opt.own_stock) {
                detail = 'Quedan ' + num(Math.max(avail, 0));
            } else {
                detail = (opt.factor === 1 ? '1 ' + item.unit_name : 'Contiene ' + num(opt.factor) + ' ' + item.unit_name) +
                    (avail === Infinity ? '' : ' · disponibles: ' + num(Math.max(avail, 0)));
            }
            var btn = $('<button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"></button>');
            btn.prop('disabled', avail < min);
            var info = $('<div></div>')
                .append($('<div class="fw-bold"></div>').text(opt.name))
                .append($('<small></small>').addClass(avail < min ? 'text-danger' : 'text-muted').text(avail < min ? 'Agotado' : detail));
            btn.append(info).append($('<span class="badge bg-success rounded-pill fs-6"></span>').text('$' + parseFloat(opt.pvp).toLocaleString('es-CL')));
            btn.on('click', function () {
                self.chooserModal.hide();
                self.addLine(item, opt);
                if (done) {
                    done();
                }
            });
            list.append(btn);
        });
        if (!this.chooserModal) {
            this.chooserModal = new bootstrap.Modal(document.getElementById('modalPresentations'));
        }
        this.chooserModal.show();
    },
    // Un producto con presentaciones sigue en la búsqueda hasta que se agreguen todas.
    getProductIds: function () {
        var self = this;
        var ids = this.detail.products.filter(value => !value.has_options || self.isFullyAdded(value.id)).map(value => value.id);
        return ids.filter((id, index) => ids.indexOf(id) === index);
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
                {data: "short_name"},
                {data: "stock"},
                {data: "cant"},
                {data: "pvp"},
                {data: "total"},
            ],
            columnDefs: [
                {
                    targets: [-5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        // Productos con presentaciones: se muestra cuál se eligió
                        if (type === 'display' && row.has_options && row.presentation_name) {
                            return $('<div>').text(data).html() + ' <span class="badge bg-info ms-1">' + $('<div>').text(row.presentation_name).html() + '</span>';
                        }
                        return data;
                    }
                },
                {
                    targets: [-4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.is_service) {
                            return 'N/A';
                        }
                        // Stock en unidades de la línea: las variantes usan el suyo; una presentación, cuántas caben en el stock
                        if (row.own_stock) {
                            data = row.row_stock;
                        } else if (row.factor && row.factor !== 1) {
                            data = row.allow_decimals ? data / row.factor : Math.floor(data / row.factor + 1e-9);
                        }
                        var shown = parseFloat(data).toLocaleString('es-CL', {maximumFractionDigits: 3});
                        if (data > 0) {
                            return '<span class="badge bg-success rounded-pill">' + shown + '</span>';
                        }
                        return '<span class="badge bg-warning rounded-pill">' + shown + '</span>';
                    }
                },
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" autocomplete="off" name="cant" value="' + row.cant + '">';
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (type !== 'display' || !sale.canEditPrice) {
                            return '$' + parseFloat(data).toLocaleString('es-CL');
                        }
                        // Quien tiene permiso puede cambiar el precio de venta de la línea (cliente especial, promoción...)
                        var changed = row.base_pvp !== undefined && parseFloat(data) !== parseFloat(row.base_pvp);
                        var original = row.base_pvp !== undefined ? '$' + parseFloat(row.base_pvp).toLocaleString('es-CL') : '';
                        return '<span title="' + (changed ? 'Precio original: ' + original : 'Editable') + '">' +
                            '<input type="text" autocomplete="off" name="pvp" class="form-control' +
                            (changed ? ' border-warning' : '') + '" value="' + parseFloat(data) + '"></span>';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + parseFloat(data).toLocaleString('es-CL');
                    }
                },
                {
                    targets: [0],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="remove" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></a>';
                    }
                },
            ],
            rowCallback: function (row, data, index) {
                var tr = $(row).closest('tr');
                var stock = sale.availableQty(data);
                if (stock === Infinity) {
                    stock = 1000000;
                }
                // Productos que se venden por peso o fracciones admiten hasta 3 decimales (0,295 kg)
                tr.find('input[name="cant"]')
                    .TouchSpin(data.allow_decimals ? {
                        min: 0.001,
                        max: stock,
                        step: 0.1,
                        decimals: 3,
                        forcestepdivisibility: 'none'   // no redondear 0,295 al múltiplo del paso
                    } : {
                        min: 1,
                        max: stock
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': data.allow_decimals ? 'decimals' : 'numbers'});
                    });

                // El precio editable se ve igual que la cantidad: campo con - y +
                var priceBase = data.base_pvp !== undefined ? data.base_pvp : data.pvp;
                tr.find('input[name="pvp"]')
                    .TouchSpin({
                        min: 0,
                        max: 9999999.99,
                        step: priceBase >= 1000 ? 100 : 1,
                        decimals: priceBase % 1 !== 0 ? 2 : 0,
                        forcestepdivisibility: 'none'
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'decimals'});
                    });

                tr.find('input[name="dscto_unitary"]')
                    .TouchSpin({
                        min: 0.00,
                        max: 100,
                        step: 0.01,
                        decimals: 2,
                        boostat: 5,
                        maxboostedstep: 10,
                        postfix: "0.00"
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'decimals'});
                    });
            },
            initComplete: function (settings, json) {

            }
        });
    },
};

$(function () {
    try {
        sale.productOptions = JSON.parse($('#product-options').text() || '{}') || {};
    } catch (e) {
        sale.productOptions = {};
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

    // referencias
    const nequiGroup = $('input[name="nequi_value"]').closest('.col');
    const daviplataGroup = $('input[name="daviplata_value"]').closest('.col');
    nequiGroup.hide();
    daviplataGroup.hide();
    // helper
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
    
    select_typemethods.on('change', function(){
        const selectedValue = $(this).val();
        if (selectedValue === 'credit') {
            expiration_date.parent().show();
            input_cash.val('0').trigger('change');
            input_change.val('0').trigger('change');
            $('input[name="total"]').val('0').trigger('change');
        } else {
            expiration_date.parent().hide();
        }
    }); 
    
    select_service_type.on('change', function(){
        const selectedValue = $(this).val();

        // Si la forma de pago es transferencia o tarjeta, llenar cash con el total
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
            if (ui.item.stock === 0 && !ui.item.is_service && !sale.hasOwnStockVariants(ui.item.id)) {
                message_error('El stock de este producto esta en 0');
                return false;
            }
            sale.pickProduct(ui.item);
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
            var tableRow = tblSearchProducts.row(tr.row);
            sale.pickProduct(row, function () {
                // Sale de la lista cuando ya no quedan presentaciones por agregar
                if (sale.isFullyAdded(row.id)) {
                    tableRow.remove().draw();
                }
            });
        });

    // Detail products

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="cant"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var item = sale.detail.products[tr.row];
            var typed = parseFloat(String($(this).val()).replace(',', '.'));
            item.cant = item.allow_decimals ? Math.round(typed * 1000) / 1000 : parseInt(typed);
            sale.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + sale.detail.products[tr.row].total.toFixed(2));
        })
        .on('change', 'input[name="pvp"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var item = sale.detail.products[tr.row];
            var typed = parseFloat(String($(this).val()).replace(',', '.'));
            if (isNaN(typed) || typed < 0 || typed >= 10000000) {
                typed = item.base_pvp !== undefined ? item.base_pvp : item.pvp;
                message_error('Ingrese un precio válido (entre 0 y 9.999.999).');
            }
            item.pvp = Math.round(typed * 100) / 100;
            var changed = item.base_pvp !== undefined && item.pvp !== item.base_pvp;
            $(this).val(item.pvp)
                .toggleClass('border-warning', changed);
            $(this).closest('span[title]')
                .attr('title', changed ? 'Precio original: $' + parseFloat(item.base_pvp).toLocaleString('es-CL') : 'Editable');
            sale.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + parseFloat(item.total).toLocaleString('es-CL'));
        })
        .on('change', 'input[name="dscto_unitary"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            sale.detail.products[tr.row].dscto = parseFloat($(this).val());
            sale.calculateInvoice();
            var parent = $(this).closest('.bootstrap-touchspin');
            parent.find('.bootstrap-touchspin-postfix').children().html(sale.detail.products[tr.row].total_dscto.toFixed(2));
            $('td:last', tblProducts.row(tr.row).node()).html('$' + sale.detail.products[tr.row].total.toFixed(2));
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
            boostat: 5,
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
            boostat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            sale.calculateChange();
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

    input_nequi_value
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
            sale.calculateChange();
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
            boostat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            sale.calculateChange();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    // Configuración global de Toastr
    toastr.options = {
        "closeButton": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "timeOut": "0",              // 👈 Nunca se cierra solo
        "extendedTimeOut": "0"
    };
    
    $('#frmForm').on('submit', function (e) {
        e.preventDefault();
        if (sale.detail.products.length === 0) {
            return message_error('Debe tener al menos 1 producto en su detalle');
        }
        if (parseFloat(input_change.val()) < 0.00) {
            return message_error('El valor recibido debe ser mayor o igual al total de la venta');
        }
        var form = $(this)[0];
        var params = new FormData(form);
        params.append('products', JSON.stringify(sale.detail.products.map(function (line) {
            var sent = $.extend({}, line);
            if (sale.canEditPrice && line.base_pvp !== undefined && line.pvp !== line.base_pvp) {
                sent.custom_price = line.pvp;   // el servidor solo lo respeta si el usuario tiene permiso
            }
            return sent;
        })));
        var url_refresh = $(this).attr('data-url');
        var args = {
            'params': params,
            'success': function (request) {
                dialog_action({
                    'content': '¿Desea imprimir la boleta de venta?',
                    'success': function () {
                        //window.open(request.print_url, '_blank');
                        //location.href = url_refresh;
                        var iframe = document.getElementById('print_frame');
                        iframe.src = request.print_url;
                        iframe.onload = function() {
                            // Cuando termine de cargar, abre el cuadro de impresión
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();

                            // Cuando se cierre el cuadro de impresión (imprimir o cancelar)
                            iframe.contentWindow.onafterprint = function() {
                                toastr.success('La factura se guardó exitosamente');
                                // 👇 Retarda la redirección 2 segundos para que se vea el toastr
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