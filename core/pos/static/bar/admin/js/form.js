var select_paymentmethod;
var select_transfermethods;
var select_autorization_discount;
var select_switch_discount;
var select_switch_cortesia;
var tblProducts, tblSearchProducts;
var input_search_product, input_birthdate, input_date_joined, input_cash, input_change, input_discount_value;
var input_description;
var sale = {
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
        this.detail.total = this.detail.subtotal + this.detail.total_iva - this.detail.total_dscto;

        $('input[name="subtotal_0"]').val(this.detail.subtotal_0.toFixed(2));
        $('input[name="subtotal_12"]').val(this.detail.subtotal_12.toFixed(2));
        $('input[name="iva"]').val(this.detail.iva.toFixed(2));
        $('input[name="total_iva"]').val(this.detail.total_iva.toFixed(2));
        $('input[name="total_dscto"]').val(this.detail.total_dscto.toFixed(2));

    },
    addProduct: function (item) {
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
                    targets: [-1, -2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(2);
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
                        max: stock
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
    input_cash = $('input[name="cash"]');
    input_total = $('input[name="total"]');
    input_change = $('input[name="change"]');
    input_search_product = $('input[name="search_product"]');
    input_birthdate = $('input[name="birthdate"]');
    input_date_joined = $('input[name="date_joined"]');
    select_paymentmethod = $('select[name="paymentmethod"]');
    select_transfermethods = $('select[name="transfermethods"]');
    select_autorization_discount = $('select[name="autorization_discount"]');
    select_switch_discount = $('#switchDescuento');
    select_switch_cortesia = $('#switchCortesia');
    input_discount_value = $('input[name="discount_value"]');
    input_description = $('input[name="description"]');

    if ($('#search_barcode').length) {
        $('#search_barcode').focus();
        $('#search_barcode').on('keypress', function(e) {

            if (e.which === 13) {

                e.preventDefault();

                let barcode = $(this).val().trim();

                if (barcode === '') {
                    return;
                }

                $.ajax({
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        action: 'search_product_barcode',
                        barcode: barcode
                    },
                    success: function(product) {

                        if (product.error) {
                            message_error('Producto no encontrado');
                            return;
                        }
                        PosCart.addProductToBarra(product);
                    }
                });
                $(this).val('').focus();
            }
        });
    }

    $('.btn-category').on('click', function () {

        $('.btn-category')
            .removeClass('btn-primary')
            .addClass('btn-outline-primary');

        $(this)
            .removeClass('btn-outline-primary')
            .addClass('btn-primary');

        const cat = $(this).data('category');

        $('.product_card').each(function () {
            const productCat = $(this).data('category');

            if (cat === "all" || productCat == cat) {
                $(this).parent().show();
            } else {
                $(this).parent().hide();
            }
        });

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
    
    $('select[name="autorization_discount"]').select2({
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

    select_autorization_discount.select2({
        theme: "bootstrap4",
        language: 'es',
        with: '100%'
    });

    // Total a pagar: con descuento (valor fijo) o cortesía (0); el método de pago lo calcula PosPayment
    PosCart.setTotalFilter(function (gross) {
        if (select_switch_cortesia.prop('checked')) return 0;
        if (select_switch_discount.prop('checked')) {
            return Math.max(gross - (parseFloat(input_discount_value.val()) || 0), 0);
        }
        return gross;
    });
    PosPayment.init();
    PosCart.refresh();

    select_autorization_discount.parent().hide();

    function toggleFields() {
        if (select_switch_discount.prop('checked')) {
            $('#discount').show();  // Mostrar si está activado
            $('#discount_value').show();  // Mostrar si está activado
            $('#description').show();  // Mostrar si está activado
        } else if (select_switch_cortesia.prop('checked')) {
            $('#discount').show();  // Mostrar si está activado
            $('#description').show();  // Mostrar si está activado
        } else {
            $('#discount').hide();  // Ocultar si no está activado
            $('#discount_value').hide();  // Ocultar si no está activado
            $('#description').hide();  // Ocultar si no está activado
        }
    }

    // Ejecutar al cargar la página
    toggleFields();

    // Ejecutar cuando se cambia el switch
    select_switch_discount.on('change', function () {
        toggleFields();
    });

    select_switch_cortesia.on('change', function () {
        toggleFields();
    });

    select_switch_discount.trigger('change');
    select_switch_cortesia.trigger('change');


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
                        return '$' + data.toFixed(2);
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

    // Carrito (producto + presentación): compartido con los pedidos de mesa
    PosCart.init();

    // Detail products

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="cant"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            sale.detail.products[tr.row].cant = parseInt($(this).val());
            sale.calculateInvoice();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + sale.detail.products[tr.row].total.toFixed(2));
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

    input_discount_value
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
            PosCart.refresh();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    select_switch_discount.on('change', function () { PosCart.refresh(); });
    select_switch_cortesia.on('change', function () { PosCart.refresh(); });

    input_date_joined.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
    });

    $('#frmForm').on('submit', function (e) {
        e.preventDefault();

        let products = PosCart.serialize();

        if (products.length === 0) {
            return message_error('Debe tener al menos 1 producto en su detalle');
        }

        var form = $(this)[0];
        var params = new FormData(form);
        params.append('action', 'add');
        params.append('products', JSON.stringify(products));
        var url_refresh = $(this).attr('data-url');
        var args = {
            'params': params,
            'success': function (request) {
                //dialog_action({
                //    'content': '¿Desea imprimir la boleta de venta?',
                //    'success': function () {
                //        window.open(request.print_url, '_blank');
                location.href = url_refresh;
                //    },
                //    'cancel': function () {
                //        location.href = url_refresh;
                //    }
                //});
            }
        };
        submit_with_formdata(args);
    });

});