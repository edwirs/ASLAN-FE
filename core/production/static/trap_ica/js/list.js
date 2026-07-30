var tblReading = {
    list: function () {
        $('#data').DataTable({
            responsive: true,
            autoWidth: false,
            destroy: true,
            ajax: {
                url: window.location.pathname,
                type: 'POST',
                data: function (d) {
                    d.action = 'search';
                    d.week_filter = $('#week_filter').val();
                },
                dataSrc: ""
            },
            columns: [
                {
                    "className": 'details-control',
                    "orderable": false,
                    "data": null,
                    "defaultContent": '<i class="fas fa-plus-circle text-primary" style="font-size: 20px; cursor: pointer;"></i>'
                },
                { "data": "date_reading" },
                { "data": "total_traps" },
                { "data": "last_observation" }
            ]
        });
    }
};

$(function () {
    tblReading.list();

    // Evento de clic en el icono para expandir
    $('#data tbody').on('click', 'td.details-control', function () {
        var tr = $(this).closest('tr');
        var row = $('#data').DataTable().row(tr);
        var icon = $(this).find('i');

        if (row.child.isShown()) {
            row.child.hide();
            tr.removeClass('shown');
            icon.removeClass('fa-minus-circle text-danger').addClass('fa-plus-circle text-primary');
        } else {
            var date = row.data().date_reading;
            $.ajax({
                url: window.location.pathname,
                type: 'POST',
                data: { 'action': 'get_detail', 'date': date },
                success: function (data) {
                    // Construimos el HTML del detalle
                    var html = '<table class="table table-sm"><thead><tr><th>Trampa</th><th>Cantidad</th></tr></thead><tbody>';
                    data.forEach(function(item) {
                        html += `<tr><td>${item.trap_name}</td><td>${item.quantity}</td></tr>`;
                    });
                    html += '</tbody></table>';
                    
                    row.child(html).show();
                    tr.addClass('shown');
                    icon.removeClass('fa-plus-circle text-primary').addClass('fa-minus-circle text-danger');
                }
            });
        }
    });
});