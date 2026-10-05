// Carrito de las pantallas de venta rápida y pedidos de mesa (producto + presentación).
//
// Requiere en la página: tabla #tblProductsBarra, campo #id_total, tarjetas .product_card
// (data-id, data-name, data-price, data-stock, data-is_service, data-unit), el JSON #product-options
// (opciones de los productos con presentaciones) y el modal #modalPresentations.
//
// Stock: en "conversión de unidades" todas las presentaciones de un producto comparten el stock del
// producto (se valida sumando las filas); en "stock por variante" cada fila usa el stock propio de su variante.
var PosCart = (function () {
    var productOptions = {};
    var chooserModal = null;
    var totalFilter = null;   // (bruto) -> total a pagar (p. ej. con descuento o cortesía)
    var payable = 0;

    function formatPrice(value) {
        return value.toLocaleString('es-CO', {style: 'currency', currency: 'COP', minimumFractionDigits: 0});
    }

    function escapeHtml(text) {
        return $('<div>').text(text === null || text === undefined ? '' : text).html();
    }

    function formatNumber(value) {
        return parseFloat(value.toFixed(3)).toLocaleString('es-CO');
    }

    // Unidades base que ya hay en el carrito de ese producto (otras filas distintas a exceptKey).
    function cartUnitsFor(productId, exceptKey) {
        var units = 0;
        $('#tblProductsBarra tbody tr').each(function () {
            var tr = $(this);
            if (tr.data('id') == productId && tr.data('key') !== exceptKey && !tr.data('own')) {
                units += (parseInt(tr.find('.input-qty').val()) || 0) * parseFloat(tr.data('factor'));
            }
        });
        return units;
    }

    // Cuántas unidades de esta presentación caben todavía.
    function availableQty(productId, factor, stock, isService, exceptKey, own) {
        if (isService) return Infinity;
        if (own) return Math.floor(stock + 1e-9);
        return Math.floor((stock - cartUnitsFor(productId, exceptKey) + 1e-9) / factor);
    }

    function stockAlert(stock, unit) {
        $.alert({
            title: 'Sin stock suficiente',
            content: 'Solo quedan ' + formatNumber(Math.max(stock, 0)) + ' ' + escapeHtml(unit || 'unidades') + ' disponibles.',
            type: 'red'
        });
    }

    function updateRow(tr) {
        var qty = parseInt(tr.find('.input-qty').val());
        if (isNaN(qty) || qty < 1) {
            qty = 1;
        }
        var own = tr.data('own') === true || tr.data('own') === 'true';
        var stock = parseFloat(tr.data('stock'));
        var max = availableQty(tr.data('id'), parseFloat(tr.data('factor')), stock,
            tr.data('service') === true || tr.data('service') === 'true', tr.data('key'), own);
        if (qty > max) {
            qty = Math.max(max, 1);
            stockAlert(own ? stock : stock - cartUnitsFor(tr.data('id'), tr.data('key')), tr.data('unit'));
        }
        tr.find('.input-qty').val(qty);
        tr.find('.price-display').text(formatPrice(qty * parseFloat(tr.data('price'))));
        updateTotal();
    }

    function updateTotal() {
        var total = 0;
        $('#tblProductsBarra tbody tr').each(function () {
            var tr = $(this);
            total += (parseInt(tr.find('.input-qty').val()) || 0) * parseFloat(tr.data('price'));
        });
        payable = totalFilter ? totalFilter(total) : total;
        $('#id_total').val(formatPrice(payable));
        $(document).trigger('poscart:changed', [payable, total]);
    }

    // item: {id, name, stock, is_service, unit, has_options}; opt: {presentation_id, name, factor, pvp, own_stock, stock}
    function appendRow(item, opt, qty) {
        var own = !!opt.own_stock;
        var rowStock = item.rowStock !== undefined ? item.rowStock : (own ? opt.stock : item.stock);
        var key = item.id + '-' + (opt.presentation_id || 0);
        var label = escapeHtml(item.name);
        if (item.has_options) {
            label += ' <span class="badge bg-info ms-1">' + escapeHtml(opt.name) + '</span>';
        }
        var row = $(
            '<tr data-id="' + item.id + '" data-key="' + key + '" data-pres="' + (opt.presentation_id || '') + '"' +
            ' data-factor="' + opt.factor + '" data-price="' + opt.pvp + '" data-stock="' + rowStock + '"' +
            ' data-own="' + (own ? 'true' : 'false') + '"' +
            ' data-service="' + (item.is_service ? 'true' : 'false') + '" data-unit="' + escapeHtml(own ? opt.name : item.unit) + '">' +
            '<td>' + label + '</td>' +
            '<td style="width:80px;"><input type="number" class="form-control form-control-sm input-qty" value="' + qty + '" min="1"></td>' +
            '<td><span class="price-display">' + formatPrice(qty * opt.pvp) + '</span>' +
            '<button type="button" class="btn btn-sm btn-danger ms-2 btn-delete" title="Eliminar"><i class="fas fa-trash-alt"></i></button></td>' +
            '</tr>'
        );
        $('#tblProductsBarra tbody').append(row);
        row.find('.input-qty').on('change', function () {
            updateRow(row);
        });
        row.find('.btn-delete').on('click', function () {
            row.remove();
            updateTotal();
        });
        return row;
    }

    // item.option = presentación elegida
    function addToCart(item) {
        var opt = item.option;
        var own = !!opt.own_stock;
        var rowStock = own ? opt.stock : item.stock;
        var key = item.id + '-' + (opt.presentation_id || 0);
        var existing = $('#tblProductsBarra tbody tr').filter(function () {
            return $(this).data('key') === key;
        });
        if (existing.length > 0) {
            var qtyInput = existing.find('.input-qty');
            qtyInput.val((parseInt(qtyInput.val()) || 0) + 1);
            updateRow(existing);
            return;
        }
        if (availableQty(item.id, opt.factor, rowStock, item.is_service, key, own) < 1) {
            stockAlert(own ? rowStock : Math.max(item.stock - cartUnitsFor(item.id, key), 0), item.unit);
            return;
        }
        appendRow(item, opt, 1);
        updateTotal();
    }

    function showChooser(item, options) {
        var list = $('#presentation_options').empty();
        var variants = options.length && options[0].own_stock;
        $('#presentation_title').text(item.name);
        $('#presentation_stock').text(item.is_service ? '' :
            (variants ? 'Stock total: ' : 'Stock: ') + formatNumber(item.stock) + (variants ? '' : ' ' + (item.unit || '')));
        options.forEach(function (opt) {
            var key = item.id + '-' + (opt.presentation_id || 0);
            var own = !!opt.own_stock;
            var avail = availableQty(item.id, opt.factor, own ? opt.stock : item.stock, item.is_service, key, own);
            var detail;
            if (own) {
                detail = 'Quedan ' + Math.max(avail, 0);
            } else {
                detail = (opt.factor === 1 ? '1 ' + escapeHtml(item.unit) : 'Contiene ' + formatNumber(opt.factor) + ' ' + escapeHtml(item.unit)) +
                    (avail === Infinity ? '' : ' &middot; disponibles: ' + Math.max(avail, 0));
            }
            var btn = $('<button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"></button>');
            btn.prop('disabled', avail < 1);
            btn.html(
                '<div><div class="fw-bold">' + escapeHtml(opt.name) + '</div>' +
                '<small class="' + (avail < 1 ? 'text-danger' : 'text-muted') + '">' + (avail < 1 ? 'Agotado' : detail) + '</small></div>' +
                '<span class="badge bg-success rounded-pill fs-6">' + formatPrice(opt.pvp) + '</span>'
            );
            btn.on('click', function () {
                chooserModal.hide();
                item.option = opt;
                addToCart(item);
            });
            list.append(btn);
        });
        if (!chooserModal) {
            chooserModal = new bootstrap.Modal(document.getElementById('modalPresentations'));
        }
        chooserModal.show();
    }

    function cardItem(card) {
        var id = card.data('id');
        var options = productOptions[id] || null;
        return {
            item: {
                id: id,
                name: card.data('name'),
                stock: parseFloat(card.data('stock')) || 0,
                is_service: card.data('is_service') === true || card.data('is_service') === 'True' || card.data('is_service') === 'true',
                unit: card.data('unit') || 'Unidad',
                has_options: !!(options && options.length > 1)
            },
            options: options,
            basePrice: parseFloat(card.data('price'))
        };
    }

    return {
        init: function () {
            productOptions = JSON.parse($('#product-options').text() || '{}');
            $(document).on('click', '.product_card', function () {
                var info = cardItem($(this));
                var item = info.item;
                // BLOQUEAR SI NO HAY STOCK
                if (!item.is_service && item.stock <= 0) {
                    $.alert({title: 'Sin stock', content: 'Este producto no tiene stock disponible', type: 'red'});
                    return;
                }
                if (item.has_options) {
                    showChooser(item, info.options);
                    return;
                }
                item.option = {presentation_id: null, name: item.unit, factor: 1, pvp: info.basePrice, own_stock: false};
                addToCart(item);
            });
        },

        // Producto devuelto por el lector de código de barras (puede traer la presentación escaneada).
        addProductToBarra: function (product) {
            var options = productOptions[product.id] || null;
            var item = {
                id: product.id,
                name: product.name,
                stock: parseFloat(product.stock) || 0,
                is_service: !!product.is_service,
                unit: product.unit_name || 'Unidad',
                has_options: !!(options && options.length > 1)
            };
            var base = options && options.length ? options[0] : {
                presentation_id: null, name: item.unit, factor: 1, pvp: parseFloat(product.pvp), own_stock: false
            };
            item.option = product.presentation || base;
            if (!item.is_service && !item.option.own_stock && item.stock <= 0) {
                $.alert({title: 'Sin stock', content: 'Este producto no tiene stock disponible', type: 'red'});
                return;
            }
            addToCart(item);
        },

        // Carga en el carrito las líneas de un pedido ya guardado.
        // d: {id, name, cant, pvp, presentation_id, presentation_name, factor, own_stock, stock, unit, is_service, has_options}
        loadRows: function (details) {
            details.forEach(function (d) {
                var opt = {
                    presentation_id: d.presentation_id, name: d.presentation_name || d.unit, factor: d.factor,
                    pvp: d.pvp, own_stock: d.own_stock, stock: d.stock
                };
                appendRow({id: d.id, name: d.name, stock: d.stock, is_service: d.is_service, unit: d.unit,
                    has_options: d.has_options}, opt, d.cant);
            });
            updateTotal();
        },

        // Total a pagar actual (después de descuento o cortesía si la pantalla los define)
        getTotal: function () {
            return payable;
        },
        setTotalFilter: function (fn) {
            totalFilter = fn;
        },
        refresh: updateTotal,

        // Líneas para enviar al servidor (el precio lo vuelve a tomar el servidor del catálogo)
        serialize: function () {
            var lines = [];
            $('#tblProductsBarra tbody tr').each(function () {
                var row = $(this);
                lines.push({
                    id: row.data('id'),
                    presentation_id: row.data('pres') || null,
                    cant: parseInt(row.find('.input-qty').val()),
                    dscto: 0.00
                });
            });
            return lines;
        }
    };
})();
