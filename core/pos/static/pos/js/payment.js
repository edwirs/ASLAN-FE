// Método de pago de la venta rápida: mismo comportamiento que el módulo Ventas.
//
// Campos del formulario: paymentmethod, transfermethods, typemethods, expiration_date, cash, propina,
// nequi_value, daviplata_value y change. El total a pagar lo entrega PosCart.getTotal().
var PosPayment = (function () {
    var $method, $transfer, $type, $expiration, $cash, $propina, $nequi, $daviplata, $change;
    var $nequiGroup, $daviplataGroup;

    function num(value) {
        return parseFloat(value) || 0;
    }

    function spin($el) {
        $el.TouchSpin({min: 0.00, max: 100000000, step: 0.01, decimals: 2, boostat: 5, maxboostedstep: 10})
            .on('keypress', function (e) {
                return validate_text_box({'event': e, 'type': 'decimals'});
            });
    }

    function toggleMixto(show) {
        $nequiGroup.toggle(show);
        $daviplataGroup.toggle(show);
    }

    // Cuánto recibió el negocio según el método y cuánto devolver (igual que en Ventas)
    function recalc(resetCash) {
        var total = PosCart.getTotal();
        var credit = $type.val() === 'credit';
        var method = $method.val();
        var transfer = $transfer.val();
        var nequi = num($nequi.val());
        var daviplata = num($daviplata.val());

        if (credit) {
            // Venta a crédito: no se recibe nada ahora
            $cash.val('0.00');
            $change.val('0.00');
            return;
        }
        if (resetCash || method !== 'cash') {
            $cash.val(total.toFixed(2));
        }
        var cash = num($cash.val());
        var received = 0;

        if (method === 'cash') {
            received = cash;
        } else if (method === 'transfer') {
            $cash.val(0);
            received = transfer === 'daviplata' ? daviplata : nequi;
        } else if (method === 'mixto') {
            if (transfer === 'mixto1') {
                var missing1 = Math.max(total - nequi, 0);
                $cash.val(missing1.toFixed(2));
                received = nequi + missing1;
            } else if (transfer === 'mixto2') {
                var missing2 = Math.max(total - daviplata, 0);
                $cash.val(missing2.toFixed(2));
                received = daviplata + missing2;
            } else if (transfer === 'mixto3') {
                $cash.val(0);
                received = nequi + daviplata;
            }
        } else if (method === 'debitCard' || method === 'creditCard') {
            $cash.val(total.toFixed(2));
            received = total;
        }
        $change.val(Math.max(received - total, 0).toFixed(2));
    }

    function onMethodChange() {
        var selected = $method.val();
        $transfer.empty();
        if (selected === 'transfer') {
            $transfer.append('<option value="nequi">Nequi</option><option value="daviplata">Daviplata</option>');
            $transfer.parent().show();
            toggleMixto(false);
        } else if (selected === 'mixto') {
            $transfer.append('<option value="mixto1">Nequi + Efectivo</option><option value="mixto2">Daviplata + Efectivo</option><option value="mixto3">Nequi + Daviplata</option>');
            $transfer.parent().show();
            toggleMixto(true);
        } else {
            $transfer.parent().hide();
            toggleMixto(false);
        }
        $nequi.val('0.00');
        $daviplata.val('0.00');
        recalc(true);
    }

    return {
        init: function () {
            $method = $('select[name="paymentmethod"]');
            $transfer = $('select[name="transfermethods"]');
            $type = $('select[name="typemethods"]');
            $expiration = $('input[name="expiration_date"]');
            $cash = $('input[name="cash"]');
            $propina = $('input[name="propina"]');
            $nequi = $('input[name="nequi_value"]');
            $daviplata = $('input[name="daviplata_value"]');
            $change = $('input[name="change"]');
            $nequiGroup = $nequi.closest('.col');
            $daviplataGroup = $daviplata.closest('.col');

            [$method, $transfer, $type].forEach(function ($s) {
                $s.select2({theme: 'bootstrap4', language: 'es'});
            });
            [$cash, $propina, $nequi, $daviplata].forEach(spin);
            $expiration.datetimepicker({useCurrent: false, format: 'YYYY-MM-DD', locale: 'es', keepOpen: false});

            $transfer.parent().hide();
            $expiration.parent().hide();
            toggleMixto(false);

            $method.on('change', onMethodChange);
            $transfer.on('change', function () { recalc(false); });
            $type.on('change', function () {
                var credit = $(this).val() === 'credit';
                $expiration.parent().toggle(credit);
                recalc(true);
            });
            $cash.on('change touchspin.on.min touchspin.on.max', function () { recalc(false); });
            $nequi.on('change touchspin.on.min touchspin.on.max', function () { recalc(false); });
            $daviplata.on('change touchspin.on.min touchspin.on.max', function () { recalc(false); });
            // Cada vez que cambia el carrito (o un descuento) el efectivo vuelve a ser el total, como en Ventas
            $(document).on('poscart:changed', function () { recalc(true); });

            onMethodChange();
        },
        recalc: recalc
    };
})();
