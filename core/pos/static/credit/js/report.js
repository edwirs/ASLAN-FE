var input_date_range;
var current_date;
var tblReport;
var select_paymentmethod;
var select_transfermethods;
var tblPayments;
var columns = [];
var report = {
    initTable: function () {
        tblReport = $('#tblReport').DataTable({
            autoWidth: false,
            destroy: true,
        });
        tblReport.settings()[0].aoColumns.forEach(function (value, index, array) {
            columns.push(value.sWidthOrig);
        });
    },
    list: function (all) {
        var parameters = {
            'action': 'search_report',
            'start_date': input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD'),
            'end_date': input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD'),
            'client_id': $('#clientSelect').val() 
        };
        if (all) {
            parameters['start_date'] = '';
            parameters['end_date'] = '';
            parameters['client_id'] = '';
        }
        tblReport = $('#tblReport').DataTable({
            destroy: true,
            autoWidth: false,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: parameters,
                dataSrc: ''
            },
            order: [[0, 'asc']],
            paging: true,
            ordering: true,
            dom: 'Bfrtip',
            buttons: [
                {
                    extend: 'excelHtml5',
                    text: ' <i class="fas fa-file-excel"></i> Descargar',
                    titleAttr: 'Excel',
                    className: 'btn btn-success btn-sm mb-3'
                },
                {
                    extend: 'pdfHtml5',
                    text: '<i class="fas fa-file-pdf"></i> Descargar',
                    titleAttr: 'PDF',
                    className: 'btn btn-danger btn-sm mb-3',
                    download: 'open',
                    orientation: 'landscape',
                    pageSize: 'LEGAL',
                    customize: function (doc) {
                        doc.styles = {
                            header: {
                                fontSize: 18,
                                bold: true,
                                alignment: 'center'
                            },
                            subheader: {
                                fontSize: 13,
                                bold: true
                            },
                            quote: {
                                italics: true
                            },
                            small: {
                                fontSize: 8
                            },
                            tableHeader: {
                                bold: true,
                                fontSize: 11,
                                color: 'white',
                                fillColor: '#2d4154',
                                alignment: 'center'
                            }
                        };
                        doc.content[1].table.widths = columns;
                        doc.content[1].margin = [0, 35, 0, 0];
                        doc.content[1].layout = {};
                        doc['footer'] = (function (page, pages) {
                            return {
                                columns: [
                                    {
                                        alignment: 'left',
                                        text: ['Fecha de creación: ', {text: current_date}]
                                    },
                                    {
                                        alignment: 'right',
                                        text: ['página ', {text: page.toString()}, ' de ', {text: pages.toString()}]
                                    }
                                ],
                                margin: 20
                            }
                        });

                    }
                }
            ],
            columns: [
                {data: "id"},
                {data: "date_joined"},
                {data: "expiration_date"},
                {data: "client.dni"},
                {data: "client.names"},
                {data: "total"},   
                {data: "pending"}, 
                {data: "paid"},
                {data: "paid"},    
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-6, -7, -8, -9],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return data;
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.total === row.paid) {
                            return '<span class="badge bg-success rounded-pill">PAGADO</span>';
                        }
                        return '<span class="badge bg-danger rounded-pill">PENDIENTE</span>';
                    }
                },
                {
                    targets: [-3, -4, -5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + parseFloat(data).toLocaleString('es-CL');
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a href="#" rel="myModalPayment" data-id="' + row.id + '" data-bs-toggle="tooltip" title="Agregar abono" class="btn btn-warning btn-sm"><i class="fas fa-money-check-dollar text-white"></i></a>';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" data-bs-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></a> ';

                        return buttons;
                    }
                },
            ],
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {

            }
        });
        $('#tblReport thead th').css('background-color', '#ffffff');
    }
};

$(function () {

    current_date = new moment().format('YYYY-MM-DD');
    input_date_range = $('input[name="date_range"]');
    select_paymentmethod = $('select[name="paymentmethod"]');
    select_transfermethods = $('select[name="transfermethods"]');

    $('#tblReport tbody')
        .off()
        .on('click', 'a[rel="myModalPayment"]', function () {
            $('.tooltip').remove();

            let id = $(this).data('id');
            $.ajax({
                url: '/pos/credit/admin/get_sale_credit/' + id + '/',
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    console.log("Respuesta del servidor:", data);
                    if (!data.error) {
                        let modalEl = $("#myModalPayment");
                        console.log("¿Existe modal en DOM?:", modalEl.length);
                        // Cargar datos en el modal
                        $('#myModalPayment').data('sale-id', data.id);
                        $('#sale_id').val(data.id);
                        $('#sale_client_dni').val(data.client.dni);
                        $('#sale_client_name').val(data.client.names);

                        $('#myModalPayment #id_date_joined').val(data.date_joined).trigger('change');
                        $('#myModalPayment #id_paymentmethod').val(data.paymentmethod.id).trigger('change');
                        $('#myModalPayment #id_transfermethods').val(data.transfermethods.id).trigger('change');

                        $('#saldo').val(data.pending);

                        // mostrar/ocultar la card de agregar abono
                        if (parseFloat(data.pending) === 0) {
                            $('#cardAddPayment').hide();
                        } else {
                            $('#cardAddPayment').show();
                        }

                        loadPayments(data.id);
                        // Mostrar modal
                        $('#myModalPayment').modal('show');
                    } else {
                        alert(data.error);
                    }
                }
            });
        });
    
    $('#btnSaveEdit').on('click', function () {
        let saleId = $('#sale_id').val();
        let paymentTotal = $('#payment_total').val();
        let paymentMethod = $('#id_paymentmethod').val();
        let transferMethod = $('#id_transfermethods').val();

        $.ajax({
            url: '/pos/credit/admin/add_payment/',
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'sale_id': saleId,
                'total': paymentTotal,
                'paymentmethod': paymentMethod,
                'transfermethods': transferMethod
            },
            success: function (response) {
                if (!response.error) {
                    alert("Pago registrado correctamente");
                    $('#myModalPayment').modal('hide');
                    report.list(false); // refresca tabla
                } else {
                    alert(response.error);
                }
            }
        });
    });

    input_date_range
        .daterangepicker({
                language: 'auto',
                startDate: new Date(),
                locale: {
                    format: 'YYYY-MM-DD',
                },
                autoApply: true,
            }
        )
        .on('change.daterangepicker apply.daterangepicker', function (ev, picker) {
            report.list(false);
        });

    $('.drp-buttons').hide();

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

    $('#clientSelect').select2({
        placeholder: 'Seleccione un cliente',
        allowClear: true,
        theme: 'bootstrap4',
        language: 'es'
    });

    select_transfermethods.parent().hide(); 
    
    select_paymentmethod.on('change', function(){
        const selectedValue = $(this).val();
        if (selectedValue === 'transfer') {
            select_transfermethods.parent().show();
        } else {
            select_transfermethods.parent().hide();
        }
    });

    //report.initTable();

    report.list(false);

    $('.btnSearchAll').on('click', function () {
        report.list(true);
    });

    $('#btnSearchClient').on('click', function () {
        report.list(false);
    });
});

function loadPayments(saleId) {
    if ($.fn.DataTable.isDataTable('#tblPayments')) {
        $('#tblPayments').DataTable().destroy();
    }
    $('#tblPayments tbody').empty();

    tblPayments = $('#tblPayments').DataTable({
        destroy: true,
        autoWidth: false,
        ajax: {
            url: '/pos/credit/admin/get_sale_payments/' + saleId + '/',
            type: 'GET',
            dataSrc: ''
        },
        columns: [
            {data: "date_payment"},
            {
                data: "total",
                render: function (data, type, row) {
                    return '$' + parseFloat(data).toLocaleString('es-CL');
                }
            },
            {data: "paymentmethod"},
            {data: "transfermethods"},
        ],
        paging: false,
        searching: false,
        ordering: false,
        info: false,
        language: {
            emptyTable: "No se han registrado pagos todavía"
        }
    });
}