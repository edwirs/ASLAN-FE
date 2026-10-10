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
        return parseFloat(value.toFixed(3)).toLocaleString('es-CO', {maximumFractionDigits: 3});
    }

    // Cantidades con hasta 3 decimales (solo productos que permiten decimales); las demás, enteras
    function round3(value) {
        return Math.round(value * 1000) / 1000;
    }

    // Solo la venta rápida (usuario con permiso) deja editar el precio de venta de cada línea.
    function canEditPrice() {
        return $('#tblProductsBarra').attr('data-edit-price') === '1';
    }

    function isDecimalRow(tr) {
        return tr.data('dec') === true || tr.data('dec') === 'true';
    }

    function readQty(tr) {
        var qty = round3(parseFloat(String(tr.find('.input-qty').val()).replace(',', '.')));
        if (isNaN(qty)) return 0;
        return isDecimalRow(tr) ? qty : Math.floor(qty);
    }

    // Unidades base que ya hay en el carrito de ese producto (otras filas distintas a exceptKey).
    function cartUnitsFor(productId, exceptKey) {
        var units = 0;
        $('#tblProductsBarra tbody tr').each(function () {
            var tr = $(this);
            if (tr.data('id') == productId && tr.data('key') !== exceptKey && !tr.data('own')) {
                units += readQty(tr) * parseFloat(tr.data('factor'));
            }
        });
        return units;
    }

    // Cuántas unidades de esta presentación caben todavía.
    function availableQty(productId, factor, stock, isService, exceptKey, own, decimals) {
        if (isService) return Infinity;
        var raw = own ? stock : (stock - cartUnitsFor(productId, exceptKey)) / factor;
        // con decimales se puede vender hasta la última fracción; sin ellos, solo unidades completas
        return decimals ? Math.floor(raw * 1000 + 1e-6) / 1000 : Math.floor(raw + 1e-9);
    }

    function stockAlert(stock, unit) {
        $.alert({
            title: 'Sin stock suficiente',
            content: 'Solo quedan ' + formatNumber(Math.max(stock, 0)) + ' ' + escapeHtml(unit || 'unidades') + ' disponibles.',
            type: 'red'
        });
    }

    function updateRow(tr) {
        var dec = isDecimalRow(tr);
        var minQty = dec ? 0.001 : 1;
        var qty = readQty(tr);
        if (!qty || qty < minQty) {
            qty = dec ? (qty > 0 ? minQty : 1) : 1;
        }
        var own = tr.data('own') === true || tr.data('own') === 'true';
        var stock = parseFloat(tr.data('stock'));
        var max = availableQty(tr.data('id'), parseFloat(tr.data('factor')), stock,
            tr.data('service') === true || tr.data('service') === 'true', tr.data('key'), own, dec);
        if (qty > max) {
            qty = Math.max(max, minQty);
            stockAlert(own ? stock : stock - cartUnitsFor(tr.data('id'), tr.data('key')), tr.data('unit'));
        }
        tr.find('.input-qty').val(qty);
        var lineTotal = qty * parseFloat(tr.data('price'));
        if (tr.find('.input-price').length) {
            // la columna Precio muestra el precio unitario editable; el subtotal solo aparece si hay varias unidades
            tr.find('.price-display').text(qty > 1 ? '= ' + formatPrice(lineTotal) : '');
        } else {
            tr.find('.price-display').text(formatPrice(lineTotal));
        }
        updateTotal();
    }

    function updateTotal() {
        var total = 0;
        $('#tblProductsBarra tbody tr').each(function () {
            var tr = $(this);
            total += readQty(tr) * parseFloat(tr.data('price'));
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
        var dec = !!item.allow_decimals;
        // Con permiso, la columna Precio es el precio unitario editable (no se agrega ningún campo más)
        var priceCell = canEditPrice() ?
            '<td><div class="d-flex align-items-start"><div>' +
            '<input type="text" inputmode="decimal" autocomplete="off" class="form-control form-control-sm input-price" style="width:90px;" title="Editar precio de venta" value="' + opt.pvp + '">' +
            '<small class="price-display text-muted d-block"></small></div>' +
            '<button type="button" class="btn btn-sm btn-danger ms-2 btn-delete" title="Eliminar"><i class="fas fa-trash-alt"></i></button></div></td>' :
            '<td><span class="price-display">' + formatPrice(qty * opt.pvp) + '</span>' +
            '<button type="button" class="btn btn-sm btn-danger ms-2 btn-delete" title="Eliminar"><i class="fas fa-trash-alt"></i></button></td>';
        var row = $(
            '<tr data-id="' + item.id + '" data-key="' + key + '" data-pres="' + (opt.presentation_id || '') + '"' +
            ' data-dec="' + (dec ? 'true' : 'false') + '"' +
            ' data-factor="' + opt.factor + '" data-price="' + opt.pvp + '" data-base-price="' + opt.pvp + '" data-stock="' + rowStock + '"' +
            ' data-own="' + (own ? 'true' : 'false') + '"' +
            ' data-service="' + (item.is_service ? 'true' : 'false') + '" data-unit="' + escapeHtml(own ? opt.name : item.unit) + '">' +
            '<td>' + label + '</td>' +
            '<td style="width:' + (dec ? '110' : '80') + 'px;"><input type="number" class="form-control form-control-sm input-qty" value="' + qty + '" ' +
            (dec ? 'min="0.001" step="0.001" inputmode="decimal"' : 'min="1" step="1"') + '></td>' +
            priceCell +
            '</tr>'
        );
        $('#tblProductsBarra tbody').append(row);
        row.find('.input-qty').on('change', function () {
            updateRow(row);
        });
        row.find('.input-price').on('input', function () {
            this.value = this.value.replace(/[^0-9.,]/g, '');
        }).on('change', function () {
            var base = parseFloat(row.data('basePrice'));
            var typed = parseFloat(String($(this).val()).replace(',', '.'));
            if (isNaN(typed) || typed < 0 || typed >= 10000000) {
                typed = base;
                $.alert({title: 'Precio inválido', content: 'Ingrese un precio entre 0 y 9.999.999.', type: 'red'});
            }
            typed = Math.round(typed * 100) / 100;
            row.data('price', typed);
            $(this).val(typed).toggleClass('border-warning', typed !== base)
                .attr('title', typed !== base ? 'Precio original: ' + formatPrice(base) : 'Editar precio de venta');
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
            qtyInput.val(round3((readQty(existing) || 0) + 1));
            updateRow(existing);
            return;
        }
        var minNeeded = item.allow_decimals ? 0.001 : 1;
        if (availableQty(item.id, opt.factor, rowStock, item.is_service, key, own, !!item.allow_decimals) < minNeeded) {
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
            var avail = availableQty(item.id, opt.factor, own ? opt.stock : item.stock, item.is_service, key, own, !!item.allow_decimals);
            var detail;
            if (own) {
                detail = 'Quedan ' + formatNumber(Math.max(avail, 0));
            } else {
                detail = (opt.factor === 1 ? '1 ' + escapeHtml(item.unit) : 'Contiene ' + formatNumber(opt.factor) + ' ' + escapeHtml(item.unit)) +
                    (avail === Infinity ? '' : ' &middot; disponibles: ' + formatNumber(Math.max(avail, 0)));
            }
            var btn = $('<button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"></button>');
            var minNeeded = item.allow_decimals ? 0.001 : 1;
            btn.prop('disabled', avail < minNeeded);
            btn.html(
                '<div><div class="fw-bold">' + escapeHtml(opt.name) + '</div>' +
                '<small class="' + (avail < minNeeded ? 'text-danger' : 'text-muted') + '">' + (avail < minNeeded ? 'Agotado' : detail) + '</small></div>' +
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
                allow_decimals: card.data('decimals') === true || card.data('decimals') === 'true',
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
                allow_decimals: !!product.allow_decimals,
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
                    allow_decimals: !!d.allow_decimals, has_options: d.has_options}, opt, d.cant);
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
                var line = {
                    id: row.data('id'),
                    presentation_id: row.data('pres') || null,
                    cant: readQty(row),
                    dscto: 0.00
                };
                // el servidor solo respeta el precio cambiado si el usuario tiene permiso
                if (canEditPrice() && parseFloat(row.data('price')) !== parseFloat(row.data('basePrice'))) {
                    line.custom_price = parseFloat(row.data('price'));
                }
                lines.push(line);
            });
            return lines;
        }
    };
})();
