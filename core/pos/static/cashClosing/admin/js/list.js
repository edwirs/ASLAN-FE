var tblcashCloshing;
var input_date_range;
var input_service_type;
var select_paymentmethod;
var select_transfermethods;
var select_service_type;
var input_cash, input_change;

var cashCloshing = {
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
        tblcashCloshing = $('#data').DataTable({
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
                {data: "created_at"},
                {data: "terminal"},
                {data: "user.names"},
                {data: "total_sales"},
                {data: "base_cash"},
                {data: "expected_cash"},
                {data: "real_cash"},
                {data: "difference"},
                {data: "tips"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [4,5,6,7,8,9],
                    className: 'text-center align-middle',

                    render: function (data) {

                        let value = parseFloat(data || 0);

                        return '$ ' + value.toLocaleString('es-CO', {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0
                        });
                    }
                },
                {
                    targets: [8],
                    className: 'text-center align-middle fw-bold',

                    render: function (data) {

                        let value = parseFloat(data || 0);

                        let color =
                            value < 0
                                ? 'text-danger'
                                : 'text-success';

                        return `
                            <span class="${color}">
                                $ ${value.toLocaleString('es-CO', {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                })}
                            </span>
                        `;
                    }
                },
                {
                    targets: [0],
                    className: 'text-center align-middle'
                },
                {
                    targets: '_all',
                    className: 'align-middle'
                },
                {
                    targets: [-1],
                    className: 'text-center align-middle',

                    render: function (data, type, row) {

                        let buttons = '';

                        if (row.print_url) {
                            buttons += `
                                <a rel="print" href="#"
                                data-url="${row.print_url}"
                                data-bs-toggle="tooltip" title="Imprimir tirilla"
                                class="btn btn-secondary btn-sm">
                                    <i class="fas fa-print"></i>
                                </a> 
                            `;
                        }

                        buttons += `
                            <a href="/pos/cashClosing/detail/${row.id}/"
                            data-bs-toggle="tooltip" title="Detalle"
                            class="btn btn-success btn-sm">
                                <i class="fas fa-eye"></i>
                            </a>
                        `;

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

    $('#data tbody')
        .off()
        .on('click', 'a[rel="print"]', function (e) {
            e.preventDefault();
            $('.tooltip').remove();

            var iframe = document.getElementById('print_frame');
            iframe.onload = function () {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            };
            iframe.src = $(this).data('url');
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
            cashCloshing.list(false);
        });

    $('.drp-buttons').hide();

    cashCloshing.list(false);

    $('.btnSearchAll').on('click', function () {
        cashCloshing.list(true);
    });

});