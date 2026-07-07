var input_date_range;

var assuranceListModule = {
    list: function (all) {
        var parameters = {
            'action': 'list',
            'start_date': input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD'),
            'end_date': input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD'),

        };
        if (all) {
            parameters['start_date'] = '';
            parameters['end_date'] = '';
        }
        $('#data').DataTable({
            responsive: true,
            scrollX: true,
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: window.location.pathname,
                type: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                data: parameters,
                dataSrc: ""
            },
            columns: [
                { data: "id" },
                { data: "date" },
                { data: "location" },
                { data: "variety" },
                { data: "auditor" },
                { data: "id" },
            ],
            columnDefs: [
                { targets: [0, 1], className: 'text-center align-middle' },
                { targets: [2], className: 'align-middle font-weight-bold' },
                { targets: [3, 4], className: 'align-middle' },
                {
                    targets: [-1],
                    className: 'text-center align-middle',
                    orderable: false,
                    render: function (data, type, row) {
                        // Botones estándar para ver detalles o editar si fuera necesario
                        return `<a href="${URL_UPDATE}${row.id}/" class="btn btn-warning btn-sm shadow-sm" data-bs-toggle="tooltip" title="Editar Registro"> <i class="fas fa-edit"></i> </a>`;
                    }
                }
            ],
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {
                enable_tooltip();
            },
            order: [[0, "desc"]], // Ordenar por ID descendente por defecto
        });
        $('#data thead th').css('background-color', '#ffffffff');
    },

    init: function () {
        input_date_range = $('input[name="date_range"]');
        
        input_date_range.daterangepicker({
            language: 'auto',
            startDate: new Date(),
            endDate: new Date(),
            locale: { format: 'YYYY-MM-DD' },
            autoApply: true,
        }).on('change.daterangepicker apply.daterangepicker', function () {
            assuranceListModule.list(false);
        });

        assuranceListModule.list(false);
    }
};

$(function () {
    assuranceListModule.init();
});