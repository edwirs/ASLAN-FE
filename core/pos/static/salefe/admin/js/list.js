var tblSale;
var input_date_range;
var select_paymentmethod;
var select_transfermethods;
var select_service_type;
var input_cash, input_change;

var sale = {
    list: function (all) {
        var parameters = {
            'action': 'search',
            'start_date': input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD'),
            'end_date': input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD'),
        };
        if (all) {
            parameters['start_date'] = '';
            parameters['end_date'] = '';
        }
        tblSale = $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: parameters,
                dataSrc: ""
            },
            order: [[0, 'desc']],
            columns: [
                {data: "id"},
                {data: "factus_invoice_id"},
                {data: "client.names"},
                {data: "date_joined"},
                {data: "total"},    
                {data: "paymentmethod.name"},
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
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a rel="detail" data-bs-toggle="tooltip" title="Detalle" class="btn btn-success btn-sm rounded-pill"><i class="fas fa-boxes"></i></a> ';
                        buttons += '<a href="#" rel="print" data-id="' + row.id + '" data-bs-toggle="tooltip" title="Imprimir" class="btn btn-secondary btn-sm rounded-pill"><i class="fas fa-print"></i></a>';                        

                        return buttons;
                    }
                },
            ],
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {
                enable_tooltip();
            }
        });
        $('#data thead th').css('background-color', '#ffffffff');
    }
};

$(function () {
    input_date_range = $('input[name="date_range"]');
    select_paymentmethod = $('select[name="paymentmethod"]');
    select_transfermethods = $('select[name="transfermethods"]');
    select_service_type = $('select[name="service_type"]');
    input_cash = $('input[name="cash"]');
    input_change = $('input[name="change"]');
    input_propina = $('input[name="propina"]');

    $('#data tbody')
        .off()
        .on('click', 'a[rel="detail"]', function () {
            $('.tooltip').remove();
            var tr = tblSale.cell($(this).closest('td, li')).index();
            var row = tblSale.row(tr.row).data();
            $('#tblProducts').DataTable({
                autoWidth: false,
                destroy: true,
                ajax: {
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        'action': 'search_detail_products',
                        'id': row.id
                    },
                    dataSrc: ""
                },
                columns: [
                    {data: "product.short_name"},
                    {data: "price_with_vat"},
                    {data: "cant"},
                    {data: "subtotal"},
                    {data: "total_dscto"},
                    {data: "total"},
                ],
                columnDefs: [
                    {
                        targets: [-1, -2, -3, -5],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '$' + parseFloat(data).toLocaleString('es-CL');
                        }
                    },
                    {
                        targets: [-4],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return data;
                        }
                    }
                ],
                initComplete: function (settings, json) {

                }
            });
            $('#myModalDetail').modal('show');
        })
        .on('click', 'a[rel="myModalEdit"]', function () {
            $('.tooltip').remove();

            let id = $(this).data('id');
            $.ajax({
                url: '/pos/salefe/admin/get_sale_Fe/' + id + '/',
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    if (!data.error) {
                        // Cargar datos en el modal
                        $('#myModalEdit').data('sale-id', data.id);
                        $('#myModalEdit #id_paymentmethod').val(data.paymentmethod.id).trigger('change');
                        $('#myModalEdit #id_transfermethods').val(data.transfermethods.id).trigger('change');
                        $('#myModalEdit #id_total').val(data.total).toLocaleString('es-CL');
                        $('#myModalEdit #id_cash').val(data.cash).toLocaleString('es-CL');
                        $('#myModalEdit #id_change').val(data.change).toLocaleString('es-CL');
                        $('#myModalEdit #id_propina').val(data.propina).toLocaleString('es-CL');

                        // Mostrar modal
                        $('#myModalEdit').modal('show');
                    } else {
                        alert(data.error);
                    }
                }
            });
        })
        .on('click', 'a[rel="print"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            let id = $(this).data('id');
            let printUrl = pathname + 'print/invoice/' + id + '/';

            var iframe = document.getElementById('print_frame');
            iframe.src = printUrl;

            iframe.onload = function () {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();

                // Cuando el usuario termina (imprimir o cancelar), regresar al listado
                var afterPrint = function () {
                    location.href = pathname;  // vuelve a la lista
                    window.removeEventListener("afterprint", afterPrint);
                };
                window.addEventListener("afterprint", afterPrint);
            };
        });

    // Guardar cambios al dar clic en "Guardar"
    $(document).on('click', '#btnSaveEdit', function () {
        let id = $('#myModalEdit').data('sale-id'); // guardamos el id de la venta al abrir la modal

        // Serializar los campos del formulario
        let formData = {
            paymentmethod: $('#id_paymentmethod').val(),
            transfermethods: $('#id_transfermethods').val(),
            typemethods: $('#id_typemethods').val(),
            total: $('#id_total').val(),
            cash: $('#id_cash').val(),
            change: $('#id_change').val(),
            propina: $('#id_propina').val(),
        };

        $.ajax({
            url: '/pos/salefe/admin/update_sale_Fe/' + id + '/',  // nueva URL para actualizar
            type: 'POST', // puede ser PUT si quieres, pero en Django normalmente usamos POST
            data: formData,
            headers: { "X-CSRFToken": csrftoken }, // csrf_token necesario
            success: function (data) {
                console.log(formData);
                if (!data.error) {
                    toastr.success('La factura se guardó exitosamente');
                        setTimeout(function() {
                            $('#myModalEdit').modal('hide');
                            location.reload();
                        }, 1000);
                } else {
                    alert("Error: " + data.error);
                }
            },
            error: function (xhr, status, error) {
                console.error(error);
                alert("Ocurrió un error al guardar los cambios ❌");
            }
        });
    });


    input_date_range.daterangepicker({
                language: 'auto',
                startDate: new Date(),
                locale: {
                    format: 'YYYY-MM-DD',
                },
                autoApply: true,
            }
        )
        .on('change.daterangepicker apply.daterangepicker', function (ev, picker) {
            sale.list(false);
        });

    $('.drp-buttons').hide();

    sale.list(false);

    $('.btnSearchAll').on('click', function () {
        sale.list(true);
    });

    $('#data tbody').on('change', '.delivered-switch', function () {
        const saleId = $(this).data('id');
        const isChecked = $(this).is(':checked');

        fetch(pathname + 'delivered/' + saleId + '/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
            }
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                alert('Error al actualizar el estado de entrega.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });

    $('select[name="paymentmethod"]').select2({
        language: 'es',
        theme: 'bootstrap4'
    });

    $('select[name="transfermethods"]').select2({
        language: 'es',
        theme: 'bootstrap4'
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
    
    select_paymentmethod.on('change', function(){
        const selectedValue = $(this).val();
        select_transfermethods.empty();
        if (selectedValue === 'transfer') {
            select_transfermethods.append('<option value="nequi">Nequi</option>');
            select_transfermethods.append('<option value="daviplata">Daviplata</option>');
            select_transfermethods.parent().show();
        } else if (selectedValue === 'mixto') {
        select_transfermethods.append('<option value="mixto1">Nequi + Efectivo</option>');
        select_transfermethods.append('<option value="mixto2">Daviplata + Efectivo</option>');
        select_transfermethods.append('<option value="mixto3">Nequi + Daviplata</option>');
        select_transfermethods.parent().show();
        } else {
            select_transfermethods.parent().hide();
        }
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
            let cash = parseFloat($(this).val()) || 0;              // lo que el usuario digitó
            let total = $('#myModalEdit #id_total').val() || 0; // el total de la venta
            let change = cash - total;                              // diferencia

            // Si el cambio es negativo, lo dejamos en 0 (opcional)
            if (change < 0) {
                change = 0;
            }

            // Asignar valor al campo change
            $('#myModalEdit #id_change').val(change);
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
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

});