var product = {
    list: function () {
        $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'action': 'search'
                },
                dataSrc: ""
            },
            columns: [
                {data: "id"},
                {data: "name"},
                {data: "code"},
                {data: "category.name"},
                {data: "stock_summary"},
                {data: "pvp"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [1],
                    render: function (data, type, row) {
                        var name = $('<div>').text(data).html();
                        if (type === 'display' && row.presentations_count) {
                            name += ' <span class="badge bg-info rounded-pill" title="Presentaciones activas">' + row.presentations_count + ' present.</span>';
                        }
                        return name;
                    }
                },
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var esc = function (t) { return $('<div>').text(t).html(); };
                        var num = function (n) { return parseFloat(n).toLocaleString('es-CO', {maximumFractionDigits: 2}); };
                        if (data.mode === 'service') {
                            return '<span class="text-muted">Sin inventario</span>';
                        }
                        if (type !== 'display') {
                            return data.total;
                        }
                        var color = function (n) { return n <= 0 ? 'bg-danger' : 'bg-success'; };
                        if (data.mode === 'variants') {
                            // Stock independiente por variante: un chip por cada una + el total
                            var chips = data.items.map(function (i) {
                                return '<span class="badge ' + color(i.stock) + ' me-1 mb-1">' + esc(i.name) + ': ' + num(i.stock) + '</span>';
                            }).join('');
                            return chips + '<div class="small text-muted">Total: ' + num(data.total) + ' &middot; por variante</div>';
                        }
                        // Conversión: un solo stock en la unidad base, y cuántas de cada presentación caben
                        var html = '<span class="badge ' + color(data.total) + '">' + num(data.total) + ' ' + esc(data.unit) + '</span>';
                        if (data.items.length) {
                            html += '<div class="small text-muted">' + data.items.map(function (i) {
                                return esc(i.name) + ': ' + num(i.stock);
                            }).join(' &middot; ') + '</div>';
                        }
                        return html;
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        
                        return '<span class="badge bg-success rounded-pill">' + '$ ' + parseFloat(data).toLocaleString('es-CL') + '</span>';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a href="' + pathname + 'update/' + row.id + '/" data-bs-toggle="tooltip" title="Editar" class="btn btn-warning btn-sm rounded-pill"><i class="fas fa-edit"></i></a> ';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" data-bs-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-sm rounded-pill"><i class="fas fa-trash"></i></a>';
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
        $('#data thead th').css('background-color', '#ffffff');
    }
};

$(function () {
    product.list();
});