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
            value.iva = lineTaxRate(value);
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

    // En táctil no se enfoca ningún campo al abrir: saldría el teclado en pantalla sobre el catálogo.
    var isTouch = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);

    if ($('#search_barcode').length) {
        if (!isTouch) {
            $('#search_barcode').focus();
        }
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
    PosCart.init({focusQtyOnSelect: true, quickMode: true});
    PosQuickUI.init(isTouch);

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
        var methodText = $.trim($('select[name="paymentmethod"] option:selected').text());
        var args = {
            'params': params,
            'title': 'Cobrar venta',
            'content': 'Se registrará la venta por <b>' + PosCart.formatPrice(PosCart.getTotal()) + '</b>' +
                (methodText ? ' (' + $('<div>').text(methodText).html() + ')' : '') + '. ¿Continuar?',
            'success': function (request) {
                // La venta ya quedó guardada: se abre el cajón (sin imprimir) y luego se recarga la pantalla.
                // Si el cajón falla (QZ Tray apagado, etc.) se da tiempo de leer el aviso antes de recargar.
                var goBack = function () {
                    location.href = url_refresh;
                };
                if (typeof CashDrawer === 'undefined') {
                    return goBack();
                }
                CashDrawer.open('bar_auto').then(function (opened) {
                    opened ? goBack() : setTimeout(goBack, 2500);
                });
            }
        };
        submit_with_formdata(args);
    });

});


// Interfaz de la venta rápida (PC con mouse y teclado, y tablet táctil): búsqueda y filtros del catálogo,
// vista tarjetas/lista, contador y botón Cobrar, billetes rápidos, atajos y hoja inferior en pantallas angostas.
var PosQuickUI = (function () {
    var VIEW_KEY = 'aslan-pos-view';
    var touch = false;
    var searchTimer = null;

    function norm(text) {
        return String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    }

    function currentCategory() {
        return String($('.btn-category.btn-primary').first().data('category'));
    }

    // Categoría + texto buscado (todas las palabras deben aparecer en código, nombre o código de barras)
    function applyFilters() {
        var cat = currentCategory();
        var raw = $('#pos_search').val() || '';
        var terms = norm(raw).split(/\s+/).filter(Boolean);
        var shown = 0;
        $('.pq-item').each(function () {
            var $item = $(this);
            var ok = cat === 'all' || String($item.data('category')) === cat;
            if (ok && terms.length) {
                var hay = $item.data('hay');
                if (hay === undefined) {
                    hay = norm($item.attr('data-search'));
                    $item.data('hay', hay);
                }
                ok = terms.every(function (t) { return hay.indexOf(t) !== -1; });
            }
            $item.toggle(ok);
            if (ok) shown++;
        });
        $('#pqEmptyGrid').toggle(shown === 0);
        $('#pqSearchBox').toggleClass('has-text', raw.length > 0);
    }

    // Con el lector de código de barras activo, el campo principal es el del lector
    function focusSearch() {
        var s = ($('#search_barcode').length ? $('#search_barcode') : $('#pos_search'))[0];
        if (s) {
            s.focus();
            s.select();
        }
    }

    function setView(view) {
        view = view === 'list' ? 'list' : 'grid';
        $('#pqProducts').toggleClass('pq-list', view === 'list');
        $('.pq-viewtoggle button').each(function () {
            $(this).toggleClass('active', $(this).data('view') === view);
        });
        try { localStorage.setItem(VIEW_KEY, view); } catch (e) { /* sin almacenamiento: se usa la vista por defecto */ }
    }

    // El panel ocupa el alto de la ventana desde donde empieza (sin barra de scroll de la página)
    function fitHeight() {
        var el = document.getElementById('posQuick');
        if (!el) return;
        var top = el.getBoundingClientRect().top + window.pageYOffset;
        el.style.height = Math.max(520, window.innerHeight - top - 40) + 'px';
    }

    function openSheet(open) {
        $('#posQuick').toggleClass('pq-open', open);
    }

    // Billetes rápidos: "Exacto" + los billetes que cubren el total (solo en efectivo)
    function renderBills(total) {
        var $b = $('#pqBills');
        var method = $('select[name="paymentmethod"]').val();
        if (method !== 'cash' || !(total > 0)) {
            $b.empty().hide();
            return;
        }
        var set = {};
        [1000, 2000, 5000, 10000, 20000, 50000, 100000].forEach(function (d) {
            if (d >= total) set[d] = true;
        });
        [5000, 10000, 50000, 100000].forEach(function (step) {
            set[Math.ceil(total / step) * step] = true;
        });
        var values = Object.keys(set).map(Number).filter(function (v) { return v > total; })
            .sort(function (a, b) { return a - b; }).slice(0, 3);
        $b.empty().show();
        $('<button type="button" class="exact"></button>').text('Exacto').attr('data-v', total).appendTo($b);
        values.forEach(function (v) {
            $('<button type="button"></button>').text(PosCart.formatPrice(v)).attr('data-v', v).appendTo($b);
        });
    }

    function updateChangeBox() {
        var change = parseFloat($('input[name="change"]').val()) || 0;
        $('#pqChange').toggleClass('has-change', change > 0);
        // el campo real conserva el número (se envía al servidor); aquí se muestra como el total: $ 30.000
        $('#pqChangeText').text(PosCart.formatPrice(change));
    }

    function onCartChanged(e, payable) {
        var n = PosCart.count();
        var money = PosCart.formatPrice(payable || 0);
        $('#pqCount').text(n + (n === 1 ? ' producto' : ' productos'));
        $('#pqEmptyCart').toggle(n === 0);
        $('#pqPay').prop('disabled', n === 0);
        $('#pqPayAmount').text(money);
        $('#pqFabCount').text(n);
        $('#pqFabTotal').text(money);
        if (n === 0) openSheet(false);
        renderBills(payable || 0);
        setTimeout(updateChangeBox, 0);
    }

    function clearSale() {
        if (PosCart.count() === 0) return;
        dialog_action({
            'content': '¿Quitar todos los productos de la venta?',
            'success': function () {
                PosCart.clear();
                if (!touch) focusSearch();
            },
            'cancel': function () {}
        });
    }

    function pay() {
        if (PosCart.count() === 0 || $('.jconfirm').length) return;
        $('#frmForm').trigger('submit');
    }

    function typingInField(target) {
        return $(target).is('input, textarea, select, [contenteditable="true"]');
    }

    return {
        init: function (isTouch) {
            touch = isTouch;
            var $search = $('#pos_search');

            // cantidad de productos por categoría
            $('.btn-category').each(function () {
                var cat = String($(this).data('category'));
                var n = cat === 'all' ? $('.pq-item').length : $('.pq-item').filter(function () {
                    return String($(this).data('category')) === cat;
                }).length;
                $('<span class="pq-cat-n"></span>').text(n).appendTo(this);
            });

            $('.btn-category').on('click', function () {
                $('.btn-category').removeClass('btn-primary').addClass('btn-outline-primary');
                $(this).removeClass('btn-outline-primary').addClass('btn-primary');
                applyFilters();
            });

            $search.on('input', function () {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(applyFilters, 90);
                $('#pqSearchBox').toggleClass('has-text', this.value.length > 0);
            }).on('keydown', function (e) {
                if (e.key === 'Escape') {
                    this.value = '';
                    applyFilters();
                    return;
                }
                if (e.key !== 'Enter') return;
                // Enter agrega el producto si solo queda uno (o el código coincide exacto) y limpia la búsqueda
                e.preventDefault();
                applyFilters();
                var typed = norm(this.value).trim();
                var $visible = $('.pq-item:visible');
                var $exact = $visible.filter(function () {
                    return norm($(this).find('.product_card').data('code')) === typed;
                });
                var $pick = $exact.length === 1 ? $exact : ($visible.length === 1 ? $visible : $());
                if ($pick.length) {
                    this.value = '';
                    applyFilters();
                    $pick.find('.product_card').trigger('click');
                }
            });
            $('#pqSearchClear').on('click', function () {
                $search.val('');
                applyFilters();
                if (!touch) focusSearch();
            });

            // las tarjetas también se activan con el teclado
            $(document).on('keydown', '.product_card', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    $(this).trigger('click');
                }
            });

            // vista tarjetas / lista (se recuerda en este equipo)
            var saved = 'grid';
            try { saved = localStorage.getItem(VIEW_KEY) || 'grid'; } catch (e) { /* sin almacenamiento */ }
            setView(saved);
            $('.pq-viewtoggle button').on('click', function () { setView($(this).data('view')); });

            // botón del cajón junto a la barra de herramientas
            $('#btnCashDrawerConfig').removeClass('btn-sm btn-secondary shadow').appendTo('#pqToolsExtra')
                .html('<i class="fas fa-cash-register"></i><span class="pq-drawer-label"> Cajón <span class="pq-key">(F2)</span></span>');

            // botones − / + de efectivo y propina: de a $1.000
            ['cash', 'propina', 'nequi_value', 'daviplata_value'].forEach(function (name) {
                var $i = $('input[name="' + name + '"]');
                $i.attr('inputmode', 'decimal');
                $i.trigger('touchspin.updatesettings', {step: 1000, boostat: 99999, maxboostedstep: 1000});
            });

            // billetes rápidos
            $('#pqBills').on('click', 'button', function () {
                $('input[name="cash"]').val((parseFloat($(this).attr('data-v')) || 0).toFixed(2)).trigger('change');
            });
            $('select[name="paymentmethod"]').on('change', function () { renderBills(PosCart.getTotal()); });
            $('#pqCart').on('change input click', function () { setTimeout(updateChangeBox, 0); });

            // contador, total del botón y estado vacío
            $(document).on('poscart:changed', onCartChanged);
            onCartChanged(null, PosCart.getTotal());

            // hoja inferior (tablet vertical)
            $('#pqFab').on('click', function () { openSheet(true); });
            $('#pqCloseCart').on('click', function () { openSheet(false); });
            $(document).on('poscart:changed', function () {
                $('#pqFab').removeClass('pq-bump');
                if (PosCart.count() > 0) {
                    void document.getElementById('pqFab').offsetWidth;
                    $('#pqFab').addClass('pq-bump');
                }
            });

            $('#pqClear').on('click', clearSale);

            // atajos: / o F3 buscar · F4 cobrar · F7 vaciar · Esc cierra la hoja (F2, el cajón, lo maneja cash_drawer.js)
            $(document).on('keydown', function (e) {
                if (e.ctrlKey || e.metaKey || e.altKey) return;
                if (e.key === 'F4') {
                    e.preventDefault();
                    pay();
                } else if (e.key === 'F7') {
                    e.preventDefault();
                    clearSale();
                } else if (e.key === 'F3' || (e.key === '/' && !typingInField(e.target))) {
                    e.preventDefault();
                    openSheet(false);
                    focusSearch();
                } else if (e.key === 'Escape' && $('#posQuick').hasClass('pq-open') && !$('.jconfirm, .modal.show').length) {
                    openSheet(false);
                }
            });

            fitHeight();
            $(window).on('resize orientationchange', fitHeight);
            setTimeout(fitHeight, 300);

            if (!touch && !$('#search_barcode').length) {
                focusSearch();
            }
            applyFilters();
        }
    };
})();
