var select_provider;
var select_paymentmethod;
var select_transfermethods;
var tblProducts, tblSearchProducts;
var input_search_product, input_birthdate, input_date_joined, input_cash, input_change;

var buy = {
    detail: {
        subtotal_0: 0.00,
        subtotal_12: 0.00,
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
            value.subtotal = value.price * value.cant;
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

        $('input[name="subtotal_0"]').val(this.detail.subtotal_0.toLocaleString('es-CL'));
        $('input[name="subtotal_12"]').val(this.detail.subtotal_12.toLocaleString('es-CL'));
        $('input[name="iva"]').val(this.detail.iva.toLocaleString('es-CL'));
        $('input[name="total_iva"]').val(this.detail.total_iva.toLocaleString('es-CL'));
        $('input[name="total_dscto"]').val(this.detail.total_dscto.toLocaleString('es-CL'));
        $('input[name="total"]').val(this.detail.total.toLocaleString('es-CL'));

        var cash = parseFloat(input_cash.val());
        var change = cash - buy.detail.total;
        input_change.val(change.toLocaleString('es-CL'));
    },
    addProduct: function (item) {
        this.detail.products.push(item);
        this.listProducts();
    },
    // Agrega un producto; si maneja presentaciones pregunta cuál se está comprando.
    // Devuelve true si se agregó de inmediato (false = quedó esperando la elección).
    pick: function (product) {
        var options = product.options || [];
        if (options.length > 1) {
            buyChooser(product, options);
            return false;
        }
        this.addPresentation(product, options[0] || {presentation_id: null, name: '', factor: 1, price: product.price});
        return true;
    },
    addPresentation: function (product, opt) {
        var hasOptions = (product.options || []).length > 1;
        var existing = this.detail.products.filter(function (v) {
            return v.id === product.id && (v.presentation_id || null) === (opt.presentation_id || null);
        })[0];
        if (existing) {
            existing.cant += 1;
            this.listProducts();
            return;
        }
        var item = $.extend({}, product);
        item.cant = 1;
        item.dscto = parseFloat(item.dscto) || 0;
        item.presentation_id = opt.presentation_id || null;
        item.presentation_name = hasOptions ? opt.name : '';
        item.factor = opt.factor;
        item.price = Math.max(parseFloat(opt.price) || 0, 1);
        item.has_options = hasOptions;
        if (opt.own_stock) {
            item.stock = opt.stock;  // variante con stock propio: se muestra el de esa variante
        }
        if (hasOptions) {
            item.short_name = product.short_name + ' - ' + opt.name;
        }
        this.addProduct(item);
    },
    getProductIds: function () {
        // Un producto con presentaciones puede repetirse (caja y six pack en la misma compra).
        return this.detail.products.filter(value => !value.has_options).map(value => value.id);
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
                {data: "price"},
                {data: "total"},
            ],
            columnDefs: [
                {
                    targets: [-5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.is_service) {
                            return '---';
                        }
                        return data;
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
                        return '<input type="text" class="form-control" autocomplete="off" name="price" value="' + data + '">';
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
                var stock = !data.is_service ? data.stock : 1000000;
                tr.find('input[name="cant"]')
                    .TouchSpin({
                        min: 1,
                        max: Number.MAX_SAFE_INTEGER
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'numbers'});
                    });
                tr.find('input[name="price"]')
                    .TouchSpin({
                        min: 1,
                        max: Number.MAX_SAFE_INTEGER
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'numbers'});
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
    select_provider = $('select[name="provider"]');
    input_cash = $('input[name="cash"]');
    input_change = $('input[name="change"]');
    input_search_product = $('input[name="search_product"]');
    input_birthdate = $('input[name="birthdate"]');
    input_date_joined = $('input[name="date_joined"]');
    select_paymentmethod = $('select[name="paymentmethod"]');
    select_transfermethods = $('select[name="transfermethods"]');

    // provider

    $('select[name="gender"]').select2({
        language: 'es',
        theme: 'bootstrap4',
        dropdownParent: $('#myModalProvider')
    });

    $('select[name="paymentmethod"]').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    $('select[name="transfermethods"]').select2({
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

    select_transfermethods.parent().hide(); 
    
    select_paymentmethod.on('change', function(){
        const selectedValue = $(this).val();
        if (selectedValue === 'transfer') {
            select_transfermethods.parent().show();
        } else {
            select_transfermethods.parent().hide();
        }
    });

    select_paymentmethod.trigger('change');

    select_provider.select2({
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
                    action: 'search_provider'
                };
            },
            processResults: function (data) {
                return {
                    results: data
                };
            },
        },
        placeholder: 'Ingrese un nombre o número de cedula de un proveedor',
        minimumInputLength: 1,
    });

    $('.btnAddProvider').on('click', function () {
        input_birthdate.datetimepicker('date', new Date());
        $('#myModalProvider').modal('show');
    });

    $('#myModalProvider').on('hidden.bs.modal', function (event) {
        $('#frmProvider')[0].reset();
    });

    $('#frmProvider').on('submit', function (e) {
        e.preventDefault();
        var form = $(this)[0];
        var params = new FormData(form);
        params.append('action', 'create_provider');
        var args = {
            'params': params,
            'success': function (request) {
                select_provider.select2('trigger', 'select', {data: request});
                $('#myModalProvider').modal('hide');
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
                    'ids': JSON.stringify(buy.getProductIds()),
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
            buy.pick(ui.item);
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
                    'ids': JSON.stringify(buy.getProductIds()),
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
        if (buy.detail.products.length === 0) return false;
        dialog_action({
            'content': '¿Estas seguro de eliminar todos los items de tu detalle?',
            'success': function () {
                buy.detail.products = [];
                buy.listProducts();
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
            var added = buy.pick(row);
            if (added) {
                tblSearchProducts.row(tr.row).remove().draw();
            }
        });

    // Detail products

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="cant"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            buy.detail.products[tr.row].cant = parseInt($(this).val());
            buy.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + buy.detail.products[tr.row].total.toFixed(2));
        })
        .on('change', 'input[name="price"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            buy.detail.products[tr.row].price = parseInt($(this).val());
            buy.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + buy.detail.products[tr.row].total.toFixed(2));
        })
        .on('change', 'input[name="dscto_unitary"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            buy.detail.products[tr.row].dscto = parseFloat($(this).val());
            buy.calculateInvoice();
            var parent = $(this).closest('.bootstrap-touchspin');
            parent.find('.bootstrap-touchspin-postfix').children().html(buy.detail.products[tr.row].total_dscto.toFixed(2));
            $('td:last', tblProducts.row(tr.row).node()).html('$' + buy.detail.products[tr.row].total.toFixed(2));
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            buy.detail.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
            buy.calculateInvoice();
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
            buy.calculateInvoice();
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
            buy.calculateInvoice();
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

    $('#frmForm').on('submit', function (e) {
        e.preventDefault();
        if (buy.detail.products.length === 0) {
            return message_error('Debe tener al menos 1 producto en su detalle');
        }
        if (parseFloat(input_change.val()) < 0.00) {
            return message_error('El efectivo debe ser mayor o igual al total de la venta');
        }
        var form = $(this)[0];
        var params = new FormData(form);
        params.append('products', JSON.stringify(buy.detail.products));
        var url_refresh = $(this).attr('data-url');
        var args = {
            'params': params,
            'success': function (request) {
                dialog_action({
                    'content': '¿Desea imprimir la boleta de venta?',
                    'success': function () {
                        window.open(request.print_url, '_blank');
                        location.href = url_refresh;
                    },
                    'cancel': function () {
                        location.href = url_refresh;
                    }
                });
            }
        };
        submit_with_formdata(args);
    });
});

// ---- Selector de presentación (compras) ---------------------------------
var chooserModal = null;

function buyChooser(product, options) {
    var money = function (v) {
        return v.toLocaleString('es-CO', {style: 'currency', currency: 'COP', minimumFractionDigits: 0});
    };
    var esc = function (t) { return $('<div>').text(t === null || t === undefined ? '' : t).html(); };
    var unit = product.unit_name || 'Unidad';
    $('#presentation_title').text(product.name);
    $('#presentation_stock').text('Stock actual: ' + parseFloat(product.stock).toLocaleString('es-CO') + ' ' + unit);
    var list = $('#presentation_options').empty();
    options.forEach(function (opt) {
        var btn = $('<button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"></button>');
        btn.html(
            '<div><div class="fw-bold">' + esc(opt.name) + '</div>' +
            '<small class="text-muted">' + (opt.own_stock ? 'Stock actual: ' + opt.stock : (opt.factor === 1 ? '1 ' + esc(unit) : 'Contiene ' + opt.factor + ' ' + esc(unit) + ' (suma ' + opt.factor + ' al stock por cada una)')) + '</small></div>' +
            '<span class="badge bg-secondary rounded-pill fs-6">' + (opt.price > 0 ? money(opt.price) : 'sin costo') + '</span>'
        );
        btn.on('click', function () {
            chooserModal.hide();
            buy.addPresentation(product, opt);
        });
        list.append(btn);
    });
    if (!chooserModal) {
        chooserModal = new bootstrap.Modal(document.getElementById('modalPresentations'));
    }
    chooserModal.show();
}
