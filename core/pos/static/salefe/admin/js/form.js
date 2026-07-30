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

        var cash = parseFloat(input_cash.val());
        var change = cash - sale.detail.total;
        input_change.val(change);
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
                {data: "name"},
                {data: "cant"},
                {data: "dscto"},
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
                    targets: [-4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" autocomplete="off" name="dscto_unitary" value="' + row.dscto_unitary + '">';
                    }
                },
                {
                    targets: [-1, -2],
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
            return message_error('El efectivo debe ser mayor o igual al total de la venta');
        }
        var form = $(this)[0];
        var params = new FormData(form);
        params.append('products', JSON.stringify(sale.detail.products));
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