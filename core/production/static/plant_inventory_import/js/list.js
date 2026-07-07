var inventoryImport = {

    list: function () {

        $('#data').DataTable({

            autoWidth: false,
            destroy: true,
            responsive: true,
            order: [[0, 'desc']],

            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    action: 'search'
                },
                dataSrc: ''
            },

            columns: [
                {data: 'id'},
                {data: 'file'},
                {data: 'imported_at'},
                {data: 'imported_by'},
                {data: 'total_records'},
                {data: 'total_created'},
                {data: 'total_updated'},
                {
                    data: 'status',
                    className: 'text-center',
                    render: function(data) {

                        if (data === 'Completado') {
                            return '<span class="badge bg-success rounded-pill">Completado</span>';
                        }

                        if (data === 'Procesando') {
                            return '<span class="badge bg-warning rounded-pill">Procesando</span>';
                        }

                        if (data === 'Pendiente') {
                            return '<span class="badge bg-secondary rounded-pill">Pendiente</span>';
                        }

                        if (data === 'Error') {
                            return '<span class="badge bg-danger rounded-pill">Error</span>';
                        }

                        return data;
                    }
                },
                {
                    data: 'id',
                    className: 'text-center',
                    render: function(data, type, row) {

                        return `
                            <a href="#" 
                            class="btn btn-primary btn-sm"
                            title="Ver detalle">
                                <i class="fas fa-eye"></i>
                            </a>
                        `;
                    }
                }
            ]
        });
    }
};

$(function () {
    inventoryImport.list();
});