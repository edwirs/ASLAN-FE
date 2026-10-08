/* =========================================================
 * FUNCION GLOBAL MONEDA
 * ========================================================= */
function formatCurrency(value) {

    value = parseFloat(value) || 0;

    return '$ ' + value.toLocaleString('es-CO', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

/* =========================================================
 * FUNCION FORMATO NUMERICO
 * ========================================================= */
function formatNumber(value) {

    value = value.toString().replace(/\D/g, '');

    if (!value.length) {
        return '';
    }

    return Number(value).toLocaleString('es-CO', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

/* =========================================================
 * VARIABLES GLOBALES
 * ========================================================= */
var tblProducts;

var input_cash;
var input_change;
var input_total;

/* =========================================================
 * OBJETO SALE
 * ========================================================= */
var sale = {

    detail: {
        subtotal_0: 0.00,
        subtotal_12: 0.00,
        subtotal: 0.00,
        dscto: 0.00,
        total_dscto: 0.00,
        iva: 19.00,
        total_iva: 0.00,
        total: 0.00,
        products: []
    },

    /* =====================================================
     * CALCULAR FACTURA
     * ===================================================== */
    calculateInvoice: function () {

        let tax = parseFloat(this.detail.iva) / 100;

        /* =====================================
         * RECORRER PRODUCTOS
         * ===================================== */
        this.detail.products.forEach(function (item) {

            item.cant = parseInt(item.cant) || 1;
            item.pvp = parseFloat(item.pvp) || 0;
            item.dscto = parseFloat(item.dscto) || 0;

            item.iva = item.with_tax ? tax : 0;

            item.subtotal = item.pvp * item.cant;

            item.total_dscto =
                item.subtotal * (item.dscto / 100);

            item.total_iva =
                (item.subtotal - item.total_dscto) * item.iva;

            item.total =
                item.subtotal -
                item.total_dscto +
                item.total_iva;
        });

        /* =====================================
         * SUBTOTALES
         * ===================================== */
        this.detail.subtotal_0 = this.detail.products
            .filter(item => !item.with_tax)
            .reduce((a, b) => a + b.total, 0);

        this.detail.subtotal_12 = this.detail.products
            .filter(item => item.with_tax)
            .reduce((a, b) => a + b.total, 0);

        this.detail.subtotal =
            this.detail.subtotal_0 +
            this.detail.subtotal_12;

        /* =====================================
         * DESCUENTO GENERAL
         * ===================================== */
        this.detail.dscto =
            parseFloat($('input[name="dscto"]').val()) || 0;

        this.detail.total_dscto =
            this.detail.subtotal *
            (this.detail.dscto / 100);

        /* =====================================
         * IVA TOTAL
         * ===================================== */
        this.detail.total_iva =
            this.detail.products.reduce(function (a, b) {
                return a + (b.total_iva || 0);
            }, 0);

        /* =====================================
         * TOTAL FINAL
         * ===================================== */
        this.detail.total =
            this.detail.subtotal -
            this.detail.total_dscto;

        /* =====================================
         * PINTAR INPUTS
         * ===================================== */
        $('input[name="subtotal_0"]')
            .val(formatCurrency(this.detail.subtotal_0));

        $('input[name="subtotal_12"]')
            .val(formatCurrency(this.detail.subtotal_12));

        $('input[name="total_iva"]')
            .val(formatCurrency(this.detail.total_iva));

        $('input[name="total_dscto"]')
            .val(formatCurrency(this.detail.total_dscto));

        input_total.val(
            formatCurrency(this.detail.total)
        );

        /* =====================================
         * CALCULAR CAMBIO
         * ===================================== */
        let cash =
            parseFloat(
                input_cash.val().replace(/\./g, '')
            ) || 0;

        let change = cash - this.detail.total;

        input_change.val(
            formatCurrency(change)
        );
    },

    /* =====================================================
     * AGREGAR PRODUCTO
     * ===================================================== */
    addProduct: function (item) {

        let found =
            this.detail.products.find(p => p.id === item.id);

        if (found) {

            found.cant += 1;

        } else {

            item.cant = 1;
            item.dscto = 0.00;

            this.detail.products.push(item);
        }

        this.listProducts();
    },

    /* =====================================================
     * IDS PRODUCTOS
     * ===================================================== */
    getProductIds: function () {

        return this.detail.products.map(item => item.id);
    },

    /* =====================================================
     * LISTAR PRODUCTOS
     * ===================================================== */
    listProducts: function () {

        this.calculateInvoice();

        tblProducts = $('#tblProducts').DataTable({

            autoWidth: false,
            destroy: true,
            data: this.detail.products,
            ordering: false,
            searching: false,
            paging: false,
            info: false,

            columns: [
                {"data": "id"},
                {"data": "short_name"},
                {"data": "stock"},
                {"data": "cant"},
                {"data": "pvp"},
                {"data": "total"},
            ],

            columnDefs: [

                {
                    targets: [0],
                    className: 'text-center align-middle',

                    render: function () {

                        return `
                            <a rel="remove"
                               class="btn btn-danger btn-sm">
                                <i class="fas fa-trash"></i>
                            </a>
                        `;
                    }
                },

                {
                    targets: [3],
                    className: 'text-center align-middle',

                    render: function (data) {

                        return `
                            <input type="number"
                                   name="cant"
                                   class="form-control text-center"
                                   min="1"
                                   value="${data}">
                        `;
                    }
                },

                {
                    targets: [4, 5],
                    className: 'text-center align-middle',

                    render: function (data) {

                        return formatCurrency(data);
                    }
                },

                {
                    targets: '_all',
                    className: 'align-middle'
                }
            ]
        });
    }
};

/* =========================================================
 * DOCUMENT READY
 * ========================================================= */
$(function () {

    /* =====================================================
     * INPUTS
     * ===================================================== */
    input_cash = $('input[name="cash"]');
    input_total = $('input[name="total"]');
    input_change = $('input[name="change"]');

    /* =====================================================
     * SELECT2
     * ===================================================== */
    $('select').select2({
        theme: 'bootstrap4',
        language: 'es'
    });

    /* =====================================================
     * TOUCHSPIN
     * ===================================================== */
    input_cash.TouchSpin({
        min: 0,
        max: 999999999,
        step: 1000,
        decimals: 0
    });

    /* =====================================================
     * EVENTOS TABLA
     * ===================================================== */
    $('#tblProducts tbody')

        .on('change', 'input[name="cant"]', function () {

            let tr =
                tblProducts.cell($(this).closest('td')).index();

            sale.detail.products[tr.row].cant =
                parseInt($(this).val()) || 1;

            sale.calculateInvoice();

            tblProducts.row(tr.row)
                .invalidate()
                .draw(false);
        })

        .on('click', 'a[rel="remove"]', function () {

            let tr =
                tblProducts.cell($(this).closest('td')).index();

            sale.detail.products.splice(tr.row, 1);

            sale.listProducts();
        });

    /* =====================================================
     * INPUT EFECTIVO
     * ===================================================== */
    if (input_cash.length > 0) {

        input_cash.on('input', function () {

            let value =
                $(this).val().replace(/\./g, '');

            if (value !== '') {

                $(this).val(
                    formatNumber(value)
                );
            }

            sale.calculateInvoice();
        });
    }

    /* =====================================================
     * INPUT BASE INICIAL
     * ===================================================== */
    $('input[name="base_cash"]').on('keyup', function () {

        let value =
            $(this).val().replace(/\./g, '');

        $(this).val(
            formatNumber(value)
        );

        calculateDifference();
    });

    /* =====================================================
     * INPUT EFECTIVO REAL
     * ===================================================== */
    $('input[name="real_cash"]').on('keyup', function () {

        let value = $(this).val();

        $(this).val(
            formatNumber(value)
        );

        calculateDifference();
    });

    /* =====================================================
     * CALCULAR DIFERENCIA
     * ===================================================== */
    function calculateDifference() {

        let expected =
            parseFloat(
                $('input[name="expected_cash_raw"]').val()
            ) || 0;

        let baseCash =
            $('input[name="base_cash"]').val() || '0';

        baseCash = parseFloat(
            baseCash.replace(/\./g, '')
        ) || 0;

        let real =
            $('input[name="real_cash"]').val() || '0';

        real = parseFloat(
            real.replace(/\./g, '')
        ) || 0;

        let isView =
            $('input[name="action"]').val() === 'view';

        if (!isView) {
            expected = expected + baseCash;
        }

        $('#expectedCashFormatted').html(
            formatCurrency(expected)
        );

        let difference = real - expected;

        let text = '';

        if (difference > 0) {

            text = `
                <span class="text-success font-weight-bold">
                    SOBRANTE:
                    ${formatCurrency(difference)}
                </span>
            `;

        } else if (difference < 0) {

            text = `
                <span class="text-danger font-weight-bold">
                    FALTANTE:
                    ${formatCurrency(Math.abs(difference))}
                </span>
            `;

        } else {

            text = `
                <span class="text-primary font-weight-bold">
                    Caja exacta
                </span>
            `;
        }

        $('#cashDifference').html(text);
    }

    /* =====================================================
     * GUARDAR CIERRE
     * ===================================================== */
    $('#frmForm').on('submit', function (e) {

        e.preventDefault();

        let realCash =
            $('input[name="real_cash"]').val();

        let baseCash =
            $('input[name="base_cash"]').val();

        if (baseCash === '') {

            message_error('Debe ingresar la base inicial');

            return false;
        }

        if (realCash === '') {

            message_error('Debe ingresar el efectivo real');

            return false;
        }

        realCash = realCash.replace(/\D/g, '');
        baseCash = baseCash.replace(/\D/g, '');

        let form = $(this)[0];

        let params = new FormData(form);

        params.set('real_cash', realCash);
        params.set('base_cash', baseCash);

        params.append('action', 'add');

        let btn = $('.btnSave');

        btn.prop('disabled', true);

        btn.html(`
            <i class="fas fa-spinner fa-spin"></i>
            Guardando cierre...
        `);

        submit_with_formdata({

            params: params,

            success: function (request) {

                var goBack = function () {
                    location.href = request.url;
                };

                // Sin permiso de impresión no se ofrece imprimir
                if (!request.print_url) {

                    $.confirm({
                        title: 'Éxito',
                        content: 'El cierre de caja fue realizado correctamente',
                        type: 'green',
                        buttons: {
                            ok: {
                                text: 'Aceptar',
                                btnClass: 'btn-success',
                                action: goBack
                            }
                        }
                    });

                    return;
                }

                dialog_action({
                    title: 'Cierre registrado',
                    content: 'El cierre de caja fue realizado correctamente. ¿Desea imprimir la tirilla?',
                    success: function () {
                        printClosingTicket(request.print_url, goBack);
                    },
                    cancel: goBack
                });
            },

            error: function () {

                btn.prop('disabled', false);

                btn.html(`
                    <i class="fas fa-save"></i>
                    Guardar cierre
                `);
            }
        });
    });

        /* =====================================================
     * SOLO LECTURA
     * ===================================================== */
    if ($('input[name="action"]').val() === 'view') {

        // Deshabilitar todos los inputs
        $('#frmForm')
            .find('input, textarea, select, button')
            .prop('disabled', true);

        // Mantener habilitado el botón volver/cancelar
        $('a.btn').removeClass('disabled');

        // Ocultar botón guardar
        $('.btnSave').hide();
    }

    /* =====================================================
     * INICIALIZAR DIFERENCIA
     * ===================================================== */
    calculateDifference();
});

/* =========================================================
 * IMPRIMIR LA TIRILLA (80 mm) DEL CIERRE
 * ========================================================= */
function printClosingTicket(url, done) {

    var iframe = document.getElementById('print_frame');

    iframe.onload = function () {

        iframe.contentWindow.focus();

        // Cuando se cierra el cuadro de impresión (imprimir o cancelar) se continúa
        iframe.contentWindow.onafterprint = function () {
            if (done) {
                done();
            }
        };

        iframe.contentWindow.print();
    };

    iframe.src = url;
}

$(function () {
    $(document).on('click', '.btnPrintClosing', function () {
        printClosingTicket($(this).data('url'), null);
    });
});
