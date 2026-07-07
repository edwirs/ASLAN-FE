var parameterModule = {
    list: function () {
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
                data: { 'action': 'list' },
                dataSrc: ""
            },
            columns: [
                { data: "id" },
                { data: "name" },
                { data: "description" },
                { data: "is_active" },
                { data: "id" },
            ],
            columnDefs: [
                { targets: [0, 3], className: 'text-center align-middle' },
                { targets: [1], className: 'align-middle font-weight-bold' },
                { targets: [2], className: 'align-middle' },
                {
                    targets: [3],
                    render: function (data, type, row) {
                        return data 
                            ? '<span class="badge badge-success p-2 cursor-pointer btnToggleStatus" data-id="'+row.id+'">ACTIVO</span>'
                            : '<span class="badge badge-secondary p-2 cursor-pointer btnToggleStatus" data-id="'+row.id+'">INACTIVO</span>';
                    }
                },
                {
                    targets: [-1],
                    className: 'text-center align-middle',
                    render: function (data, type, row) {
                        return '<button type="button" class="btn btn-warning btn-sm btnEditParameter"><i class="fas fa-edit"></i></button>';
                    }
                }
            ],
            createdRow: function (row, data, dataIndex) {
                $(row).attr('data-item', JSON.stringify(data));
            }
        });
    },

    bindEvents: function () {
        // 1. Delegación de evento: Esto hace que el botón que viene del padre funcione
        $(document).on('click', '.btnAddParameter', function (e) {
            e.preventDefault(); // Evita que el enlace # navegue
            $('#formParameter')[0].reset();
            $('#param_id').val('');
            $('#parameterModalTitle span').text('Nuevo Parámetro');
            $('#parameterModal').modal('show');
        });

        // 2. Evento para editar
        $(document).on('click', '.btnEditParameter', function () {
            let item = JSON.parse($(this).closest('tr').attr('data-item'));
            $('#param_id').val(item.id);
            $('#param_name').val(item.name);
            $('#param_description').val(item.description);
            $('#param_is_active').prop('checked', item.is_active);
            $('#parameterModal').modal('show');
        });

        // 3. Evento para cambiar estado
        $(document).on('click', '.btnToggleStatus', function () {
            parameterModule.toggleStatus($(this).data('id'));
        });

        // 4. Envío del formulario
        $('#formParameter').on('submit', function (e) {
            e.preventDefault();
            let formData = new FormData(this);
            formData.append('action', 'save');
            formData.set('is_active', $('#param_is_active').is(':checked'));
            
            $.ajax({
                url: window.location.pathname,
                type: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                data: formData,
                processData: false,
                contentType: false,
                success: function () {
                    $('#parameterModal').modal('hide');
                    parameterModule.list();
                }
            });
        });
    },

    toggleStatus: function (id) {
        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: { 'action': 'toggle_status', 'id': id },
            success: function () { parameterModule.list(); }
        });
    },

    init: function () {
        // Forzar que el enlace de "Nuevo Registro" del padre tenga la clase correcta
        $('a[href="#"]').addClass('btnAddParameter');
        
        this.bindEvents();
        this.list();
    }
};

$(function () {
    parameterModule.init();
});