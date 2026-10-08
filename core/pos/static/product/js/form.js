var input_is_service;
var input_description;

$(function () {
    input_is_service = $('input[name="is_service"]');
    input_description = $('input[name="description"]');
    
    $('.select2').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    // El stock admite hasta 3 decimales solo si el producto permite cantidades decimales
    var $allowDecimals = $('input[name="allow_decimals"]');
    var $stock = $('input[name="stock"]');
    $stock
        .TouchSpin({
            min: 0,
            max: 100000000,
            step: 1,
            decimals: 0,
            forcestepdivisibility: 'none',
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': $allowDecimals.is(':checked') ? 'decimals' : 'numbers'});
        });
    function applyStockMode() {
        var decimals = $allowDecimals.is(':checked');
        $stock.trigger('touchspin.updatesettings', {decimals: decimals ? 3 : 0, step: 1});
    }
    $allowDecimals.on('change', applyStockMode);
    applyStockMode();

    $('input[name="price"]')
        .TouchSpin({
            min: 0.01,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            maxboostedstep: 10,
            prefix: '$'
        })
        .on('change touchspin.on.min touchspin.on.max', function () {
            $('input[name="pvp"]').trigger("touchspin.updatesettings", {min: parseFloat($(this).val())});
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    $('input[name="pvp"]')
        .TouchSpin({
            min: 0.01,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            maxboostedstep: 10,
            prefix: '$'
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });
    
    function toggleFields() {
        if (input_is_service.prop('checked')) {
            $('#price, #stock, #min_stock').hide(); // Oculta los divs con los inputs
        } else {
            $('#price, #stock, #min_stock').show(); // Muestra los divs
        }
    }

    // Ejecutar al cargar la página
    toggleFields();

    // Ejecutar cuando se cambia el switch
    input_is_service.on('change', function () {
        toggleFields();
    });

    input_is_service.trigger('change');

    $('input[name="code"]')
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'numbers_letters'});
        })
        .on('keyup', function (e) {
            var value = $(this).val();
            $(this).val(value.toUpperCase());
        });
});

// ---- Unidad de medida (selector con opción "Otra…") --------------------------
function getUnitName() {
    var value = $('select[name="unit_name"]').val();
    if (value === '__other__') {
        return $.trim($('#unit_name_other').val()) || 'Unidad';
    }
    return value || 'Unidad';
}

$(function () {
    var $select = $('select[name="unit_name"]');
    var $other = $('#unit_name_other');
    function toggleOther() {
        var other = $select.val() === '__other__';
        $other.toggle(other);
        if (other) $other.trigger('focus');
    }
    $select.on('change', toggleOther);
    toggleOther();

    // Al elegir una unidad que se vende en fracciones (Kilo, Libra, Litro...), se activa solo
    // "¿Permite cantidades decimales?". Si el usuario lo cambia a mano, se respeta su decisión.
    var decimalUnits = [];
    try { decimalUnits = JSON.parse($select.attr('data-decimal-units') || '[]'); } catch (e) { decimalUnits = []; }
    var $allow = $('input[name="allow_decimals"]');
    var $hint = $('#decimals_hint');
    var autoChecked = false;

    function showHint(text) {
        if (text) {
            $hint.text(text).each(function () { this.style.setProperty('display', 'block', 'important'); });
        } else {
            $hint.each(function () { this.style.setProperty('display', 'none', 'important'); });
        }
    }

    $allow.on('change', function (e) {
        if (!e.isTrigger) {
            autoChecked = false;
            showHint('');
        }
    });

    $select.on('change', function () {
        var unit = $select.val();
        if (decimalUnits.indexOf(unit) !== -1) {
            if (!$allow.is(':checked')) {
                $allow.prop('checked', true).trigger('change');
                autoChecked = true;
                showHint('Se activó porque «' + unit + '» se vende en fracciones. Puede desactivarlo si no lo necesita.');
            }
        } else if (autoChecked && $allow.is(':checked')) {
            $allow.prop('checked', false).trigger('change');
            autoChecked = false;
            showHint('');
        }
    });
});

// ---- Presentaciones -------------------------------------------------------
var presentations = {
    $body: null,

    mode: function () {
        return $('input[name="presentation_mode"]:checked').val() || 'conversion';
    },

    init: function () {
        var self = this;
        self.$body = $('#tblPresentations tbody');
        JSON.parse($('#presentations-data').text() || '[]').forEach(function (row) {
            self.addRow(row);
        });

        $('#btn_add_presentation').on('click', function () {
            self.addRow({name: '', factor: '', price: '', pvp: '', barcode: '', stock: '', is_active: true});
            self.$body.find('tr:last .p-name').focus();
            self.refresh();
        });

        self.$body.on('input change', 'input', function () {
            self.refresh();
        });
        self.$body.on('click', '.btn-remove', function () {
            $(this).closest('tr').remove();
            self.refresh();
        });
        $('select[name="unit_name"], #unit_name_other, input[name="pvp"]').on('input change', function () {
            self.refresh();
        });

        // Las presentaciones solo se editan (y se ofrecen en las ventas) si el switch está activo.
        $('input[name="uses_presentations"]').on('change', function () {
            self.toggle();
            if ($(this).is(':checked') && self.$body.find('tr').length === 0) {
                $('#btn_add_presentation').trigger('click');
            }
        });
        $('input[name="presentation_mode"]').on('change', function () {
            self.toggle();
        });
        self.toggle();
    },

    toggle: function () {
        var on = $('input[name="uses_presentations"]').is(':checked');
        var variants = this.mode() === 'variants';
        $('#presentations_body').toggle(on);
        $('#presentations_off').toggle(!on);
        $('#presentations_card').toggleClass('mode-variants', variants);
        $('.mode-conv').toggle(!variants);
        $('.mode-var').toggle(variants);
        $('.help-conv').toggle(!variants);
        $('.help-var').toggle(variants);
        $('.mode-option').removeClass('active').find('input:checked').closest('.mode-option').addClass('active');
        var unit = getUnitName();
        // En variantes el stock de arriba es el de la unidad base, que es una variante más
        $('#stock label.stock').contents().first().replaceWith(on && variants ? 'Stock de ' + unit + ' ' : 'Stock ');
        $('#stock .base-hint').toggle(!(on && variants));
        this.$body.find('.p-name').attr('placeholder', this.namePlaceholder());
        this.refresh();
    },

    namePlaceholder: function () {
        return this.mode() === 'variants' ? 'Ej: Talla M, Fresa, Grande' : 'Ej: Caja x12, Kilo';
    },

    addRow: function (r) {
        var esc = function (v) { return $('<div>').text(v === null || v === undefined ? '' : v).html().replace(/"/g, '&quot;'); };
        var tr = $(
            '<tr data-id="' + esc(r.id || '') + '">' +
            '<td><input type="text" class="form-control form-control-sm p-name" maxlength="50" placeholder="' + this.namePlaceholder() + '" value="' + esc(r.name) + '"></td>' +
            '<td class="mode-conv"><input type="number" class="form-control form-control-sm p-factor" min="0.001" step="0.001" placeholder="12" value="' + esc(r.factor) + '"></td>' +
            '<td class="mode-var"><input type="number" class="form-control form-control-sm p-stock" min="0" step="any" placeholder="0" value="' + esc(r.stock) + '"></td>' +
            '<td><input type="number" class="form-control form-control-sm p-price" min="0" step="0.01" value="' + esc(r.price) + '"></td>' +
            '<td><input type="number" class="form-control form-control-sm p-pvp" min="0.01" step="0.01" value="' + esc(r.pvp) + '"></td>' +
            '<td><input type="text" class="form-control form-control-sm p-barcode" maxlength="50" value="' + esc(r.barcode) + '"></td>' +
            '<td class="text-center text-muted p-unit mode-conv">-</td>' +
            '<td class="text-center"><div class="form-check form-switch d-flex justify-content-center mb-0"><input type="checkbox" class="form-check-input p-active"' + (r.is_active === false ? '' : ' checked') + '></div></td>' +
            '<td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger btn-remove" title="Quitar"><i class="fas fa-trash"></i></button></td>' +
            '</tr>'
        );
        this.$body.append(tr);
        var variants = this.mode() === 'variants';
        tr.find('.mode-conv').toggle(!variants);
        tr.find('.mode-var').toggle(variants);
    },

    rows: function () {
        return this.$body.find('tr').map(function () {
            var $tr = $(this);
            return {
                id: $tr.data('id') || null,
                name: $.trim($tr.find('.p-name').val()),
                factor: $tr.find('.p-factor').val(),
                stock: $tr.find('.p-stock').val(),
                price: $tr.find('.p-price').val() || '0',
                pvp: $tr.find('.p-pvp').val(),
                barcode: $.trim($tr.find('.p-barcode').val()),
                is_active: $tr.find('.p-active').is(':checked')
            };
        }).get();
    },

    refresh: function () {
        var unit = getUnitName();
        $('.unit-label').text(unit);
        var base = parseFloat($('input[name="pvp"]').val()) || 0;
        this.$body.find('tr').each(function () {
            var f = parseFloat($(this).find('.p-factor').val());
            var pvp = parseFloat($(this).find('.p-pvp').val());
            var $cell = $(this).find('.p-unit');
            if (f > 0 && pvp > 0) {
                var per = pvp / f;
                var cls = base && per > base ? 'text-danger' : (base && per < base ? 'text-success' : '');
                $cell.html('<span class="' + cls + '">$' + per.toLocaleString('es-CO', {maximumFractionDigits: 2}) + '</span>');
            } else {
                $cell.text('-');
            }
        });
        $('#presentations_empty').toggle(this.$body.find('tr').length === 0);
        $('#id_presentations').val(JSON.stringify(this.rows()));
    }
};

$(function () {
    presentations.init();
});


// ---- Imagen del producto: validación y vista previa antes de enviar ----------
$(function () {
    var MAX_BYTES = 2 * 1024 * 1024;
    var TYPES = ['image/jpeg', 'image/png', 'image/webp'];
    var $input = $('#id_image');
    var $preview = $('#image_preview');
    var original = $preview.html();

    $input.on('change', function () {
        var file = this.files && this.files[0];
        if (!file) {
            $preview.html(original);
            return;
        }
        var problem = null;
        if (TYPES.indexOf(file.type) === -1) {
            problem = 'El archivo debe ser una imagen JPG, PNG o WebP.';
        } else if (file.size > MAX_BYTES) {
            problem = 'La imagen pesa ' + (file.size / 1024 / 1024).toFixed(1) + ' MB y el máximo es 2 MB. Use una imagen más pequeña.';
        }
        if (problem) {
            $input.val('');
            $preview.html(original);
            message_error(problem);
            return;
        }
        var url = URL.createObjectURL(file);
        $preview.html('<img src="' + url + '" alt="" style="max-width:100%;max-height:100%;object-fit:contain;">');
        $('#image-clear').prop('checked', false);
    });
});
