$(function () {
    const selectCategory = $('select[name="category"]');
    const fieldExternal = $('input[name="external_trap"]');
    const fieldInternal = $('input[name="internal_trap"]');

    function updateTrapFields(categoryId) {
        // Si no hay categoría seleccionada, bloqueamos y salimos
        if (!categoryId || categoryId === "") {
            fieldExternal.prop('disabled', true).prop('checked', false);
            fieldInternal.prop('disabled', true).prop('checked', false);
            return;
        }

        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: {
                'action': 'get_category',
                'id': categoryId
            },
            success: function (data) {
                // Aquí validamos lo que viene del servidor
                if (data.handle_traps) {
                    fieldExternal.prop('disabled', false);
                    fieldInternal.prop('disabled', false);
                } else {
                    fieldExternal.prop('disabled', true).prop('checked', false);
                    fieldInternal.prop('disabled', true).prop('checked', false);
                }
            },
            error: function (e) {
                console.log("Error en AJAX:", e);
            }
        });
    }

    // 1. Evento cuando el usuario cambia la categoría manualmente
    selectCategory.on('change', function () {
        updateTrapFields($(this).val());
    });

    // 2. Ejecutar inmediatamente al cargar la página
    // Esto es vital para el modo Edición y para el modo Crear
    updateTrapFields(selectCategory.val());
});