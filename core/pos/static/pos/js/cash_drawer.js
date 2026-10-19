// Cajón monedero: se abre con la tecla F2 sin imprimir nada.
//
// El servidor está en un VPS, así que el navegador le pide a QZ Tray (programa instalado en el PC de caja,
// https://qz.io/download/) que mande el comando ESC/POS de apertura a la impresora térmica.
// La impresora y el pin se eligen una vez por computador y se guardan en localStorage.
var CashDrawer = (function () {
    var HOTKEY = 'F2';
    var STORAGE_KEY = 'aslan-cash-drawer';
    var DEFAULTS = {printer: '', pin: 0};
    var MIN_INTERVAL_MS = 700;   // evita aperturas repetidas si la tecla queda presionada

    var logUrl = '';
    var certUrl = '';
    var signUrl = '';
    var source = '';
    var pending = null;   // apertura en curso
    var lastOpen = 0;
    var modal = null;

    function load() {
        try {
            var saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            return {printer: saved.printer || '', pin: parseInt(saved.pin, 10) === 1 ? 1 : 0};
        } catch (e) {
            return {printer: DEFAULTS.printer, pin: DEFAULTS.pin};
        }
    }

    function save(cfg) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
            return true;
        } catch (e) {
            return false;
        }
    }

    function toast(icon, title) {
        Swal.fire({toast: true, position: 'top-end', icon: icon, title: title, showConfirmButton: false, timer: 3500});
    }

    function friendly(err) {
        var text = (err && err.message) ? err.message : String(err || '');
        if (/establish connection|websocket|Unable to connect|connection/i.test(text)) {
            return 'No hay conexión con QZ Tray. Verifique que esté instalado y en ejecución (ícono junto al reloj de Windows).';
        }
        if (/printer/i.test(text)) {
            return 'No se encontró la impresora. Revise la configuración del cajón (botón "Cajón (F2)").';
        }
        return text || 'No se pudo abrir el cajón';
    }

    // Firma de las peticiones: QZ Tray exige identificar al sitio para poder "recordar" la autorización.
    // El certificado público y la firma los entrega el servidor (la llave privada nunca sale de él).
    function setupSigning() {
        if (!certUrl || !signUrl || typeof qz === 'undefined') {
            return;
        }
        qz.security.setCertificatePromise(function (resolve, reject) {
            fetch(certUrl, {credentials: 'same-origin'}).then(function (r) {
                return r.ok ? r.text() : Promise.reject(new Error('Certificado no disponible'));
            }).then(resolve, function (err) {
                console.warn('QZ Tray: se usará petición sin firmar.', err);
                reject(err);   // sin certificado QZ trata la petición como anónima (pide permiso cada vez)
            });
        });
        qz.security.setSignatureAlgorithm('SHA512');
        qz.security.setSignaturePromise(function (toSign) {
            return function (resolve, reject) {
                fetch(signUrl, {
                    method: 'POST',
                    headers: {'X-CSRFToken': csrfToken()},
                    body: new URLSearchParams({request: toSign}),
                    credentials: 'same-origin'
                }).then(function (r) {
                    return r.ok ? r.text() : Promise.reject(new Error('No se pudo firmar la solicitud'));
                }).then(resolve, function (err) {
                    console.warn('QZ Tray: no se pudo firmar la solicitud.', err);
                    resolve();
                });
            };
        });
    }

    function connect() {
        if (typeof qz === 'undefined') {
            return Promise.reject(new Error('No se pudo cargar QZ Tray'));
        }
        if (qz.websocket.isActive()) {
            return Promise.resolve();
        }
        return qz.websocket.connect({retries: 1, delay: 1});
    }

    function resolvePrinter(cfg) {
        return cfg.printer ? Promise.resolve(cfg.printer) : qz.printers.getDefault();
    }

    function csrfToken() {
        var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input) {
            return input.value;
        }
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    // Registro de auditoría: solo se envía cuando el cajón realmente se abrió. Si falla no afecta la venta.
    function log(from, printer) {
        if (!logUrl) {
            return;
        }
        var body = new URLSearchParams({source: from, printer: printer});
        fetch(logUrl, {
            method: 'POST',
            headers: {'X-CSRFToken': csrfToken()},
            body: body,
            credentials: 'same-origin'
        }).catch(function () {});
    }

    // ESC p m t1 t2: pulso de apertura. m = pin (0 → pin 2, 1 → pin 5), t1 = 50 ms, t2 = 500 ms.
    function command(pin) {
        return '1B70' + ('0' + pin).slice(-2) + '19FA';
    }

    function open(from, override) {
        if (pending) {
            return pending;
        }
        if (Date.now() - lastOpen < MIN_INTERVAL_MS) {
            return Promise.resolve(true);   // se acaba de abrir (p. ej. F2 justo antes de guardar)
        }
        var cfg = override || load();
        var printerName = '';
        pending = connect()
            .then(function () {
                return resolvePrinter(cfg);
            })
            .then(function (printer) {
                printerName = printer;
                var data = [{type: 'raw', format: 'command', flavor: 'hex', data: command(cfg.pin)}];
                return qz.print(qz.configs.create(printer), data);
            })
            .then(function () {
                lastOpen = Date.now();
                log(from, printerName);
                return true;
            })
            .catch(function (err) {
                toast('error', friendly(err));
                return false;
            })
            .then(function (ok) {
                pending = null;
                return ok;
            });
        return pending;
    }

    function $(id) {
        return document.getElementById(id);
    }

    function fillPrinters(selected) {
        var select = $('cdPrinter');
        var status = $('cdStatus');
        select.innerHTML = '<option value="">Impresora predeterminada de Windows</option>';
        return connect()
            .then(function () {
                return qz.printers.find();
            })
            .then(function (printers) {
                [].concat(printers || []).forEach(function (name) {
                    var option = document.createElement('option');
                    option.value = name;
                    option.textContent = name;
                    select.appendChild(option);
                });
                if (selected && ![].slice.call(select.options).some(function (o) { return o.value === selected; })) {
                    var missing = document.createElement('option');
                    missing.value = selected;
                    missing.textContent = selected + ' (no detectada)';
                    select.appendChild(missing);
                }
                select.value = selected || '';
                status.className = 'alert alert-success py-2 small mb-3';
                status.textContent = 'QZ Tray conectado. Impresoras detectadas: ' + (printers ? [].concat(printers).length : 0) + '.';
            })
            .catch(function (err) {
                status.className = 'alert alert-danger py-2 small mb-3';
                status.textContent = friendly(err);
            });
    }

    function showConfig() {
        var cfg = load();
        $('cdPin').value = String(cfg.pin);
        var status = $('cdStatus');
        status.className = 'alert alert-secondary py-2 small mb-3';
        status.textContent = 'Conectando con QZ Tray...';
        modal.show();
        fillPrinters(cfg.printer);
    }

    function formValues() {
        return {printer: $('cdPrinter').value, pin: parseInt($('cdPin').value, 10) === 1 ? 1 : 0};
    }

    function init(options) {
        logUrl = options.logUrl || '';
        certUrl = options.certUrl || '';
        signUrl = options.signUrl || '';
        setupSigning();
        source = options.source || '';
        modal = new bootstrap.Modal($('modalCashDrawer'));

        document.addEventListener('keydown', function (e) {
            if (e.key !== HOTKEY) {
                return;
            }
            e.preventDefault();
            if (!e.repeat) {
                open(source);
            }
        });

        $('btnCashDrawerConfig').addEventListener('click', showConfig);
        $('cdTest').addEventListener('click', function () {
            open('test', formValues()).then(function (ok) {
                if (ok) {
                    toast('success', 'Se envió la orden de apertura al cajón');
                }
            });
        });
        $('cdSave').addEventListener('click', function () {
            if (save(formValues())) {
                toast('success', 'Configuración del cajón guardada en este equipo');
                modal.hide();
            } else {
                toast('error', 'El navegador no permite guardar la configuración');
            }
        });
    }

    return {init: init, open: open};
})();
