var transaction = {
    list: function () {
        $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            responsive: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    action: 'search'
                },
                dataSrc: ""
            },
            columns: [
                {data: "employee"},           // empleado
                {data: "transaction_type"},   // tipo
                {data: "source"},             // origen
                {data: "amount"},             // valor
                {data: "created_at"},         // fecha
                {data: "id"}                  // botones
            ],
            columnDefs: [

                // MONTO
                {
                    targets: [3],
                    class: 'text-center',
                    render: function (data) {
                        return '$ ' + parseFloat(data).toLocaleString('es-CO');
                    }
                },

                // BOTONES
                {
                    targets: [-1],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {

                        var buttons = '';

                        buttons += '<a href="'+ pathname +'/update/'+ row.id +'/" class="btn btn-warning btn-sm" title="Editar"><i class="fas fa-edit"></i></a> ';

                        buttons += '<a href="'+ pathname +'/delete/'+ row.id +'/" class="btn btn-danger btn-sm" title="Eliminar"><i class="fas fa-trash"></i></a> ';

                        buttons += '<button data-id="'+row.id+'" class="btn btn-secondary btn-sm btn-print"><i class="fas fa-print"></i></button>';

                        return buttons;
                    }
                }
            ],
            rowCallback: function (row, data) {

            },
            initComplete: function () {
                enable_tooltip();
            }
        });

        $('#data thead th').css('background-color', '#ffffff');
    }
};

$(function () {
    transaction.list();

    $('#data tbody').on('click', '.btn-print', function(){

        let id = $(this).data('id');

        let iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        document.body.appendChild(iframe);

        iframe.src = pathname + '/print/transaction/' + id + '/';

        iframe.onload = function(){
            iframe.contentWindow.focus();
            iframe.contentWindow.print();

            iframe.contentWindow.onafterprint = function(){
                iframe.remove();
            };
        };

    });
});