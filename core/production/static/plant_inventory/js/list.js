var tblInventory = null;

function getData() {

    tblInventory = $('#data').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        deferRender: true,
        searching: false,
        initComplete: function () {
            $('#data_filter').hide();
        },
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            data: {
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
                action: 'search',
                code: $('#code').val(),
                plot_id: $('#plot_id').val(),
                location: $('#location').val(),
                genus: $('#genus').val(),
                area: $('#area').val()
            },
            dataSrc: ""
        },
        columns: [
            {"data": "code"},
            {"data": "plot_id"},
            {"data": "location"},
            {"data": "variety"},
            {"data": "genus"},
            {"data": "area"},
            {"data": "plants"}
        ]
    });
}

$(function () {

    $('.btnSearch').on('click', function () {

        let code = $('#code').val().trim();
        let plot_id = $('#plot_id').val().trim();
        let location = $('#location').val().trim();
        let genus = $('#genus').val().trim();
        let area = $('#area').val().trim();

        if (
            code === '' &&
            plot_id === '' &&
            location === '' &&
            genus === '' &&
            area === ''
        ) {

            Swal.fire({
                icon: 'warning',
                title: 'Filtros requeridos',
                text: 'Debe ingresar al menos un filtro para realizar la consulta.'
            });

            return;
        }

        getData();

    });

});