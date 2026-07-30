// create.js - Trampas Externas

document.addEventListener("DOMContentLoaded", function() {
    console.log("¡El archivo JS externo de trampas externas cargó correctamente!");

    // 1. Cargar las trampas externas disponibles al iniciar la vista
    loadAvailableExternalTraps();

    // 2. Evento cuando selecciona una Trampa Externa específica para mostrar la matriz
    $('#select_trap').on('change', function() {
        let trapId = $(this).val();
        if (trapId) {
            $('#matrix_container').fadeIn();
        } else {
            $('#matrix_container').hide();
        }
    });

    // 3. Control de botones Incremento (+) y Decremento (-)
    $(document).on('click', '.qty-btn', function() {
        let btn = $(this);
        let action = btn.data('action');
        let container = btn.closest('.input-controls-row');
        let input = container.find('.input-qty');
        let val = parseInt(input.val()) || 0;

        if (action === 'inc') {
            val += 1;
        } else if (action === 'dec') {
            val = val > 0 ? val - 1 : 0;
        }

        input.val(val);
        input.css('background-color', val > 0 ? '#fff3cd' : '#ffffff');
    });

    // Cambio de color manual en el input si escriben directamente
    $(document).on('input', '.input-qty', function() {
        let val = parseInt($(this).val()) || 0;
        $(this).css('background-color', val > 0 ? '#fff3cd' : '#ffffff');
    });

    // 4. Confirmación y envío del formulario por JSON incluyendo cantidades y observaciones
    $(document).on('click', 'button[type="submit"], input[type="submit"], .btn-save', function(e) {
        e.preventDefault();

        let dateReading = $('input[name="date_reading"]').val();
        let trapId = $('#select_trap').val();

        if (!dateReading) {
            Swal.fire('Error', 'Por favor seleccione una fecha de lectura.', 'warning');
            return;
        }

        if (!trapId) {
            Swal.fire('Error', 'Por favor seleccione una trampa externa.', 'warning');
            return;
        }

        // Recolectamos cantidades recorriendo las tarjetas de la matriz
        let targetsData = {};
        
        $('.input-qty').each(function() {
            let inputQty = $(this);
            let inputName = inputQty.attr('name'); // qty_{target_id}
            let parts = inputName.split('_');
            
            if (parts.length === 2) {
                let targetId = parts[1];
                let qtyVal = parseInt(inputQty.val()) || 0;

                // Guardamos si tiene cantidad mayor a 0
                if (qtyVal > 0) {
                    targetsData[targetId] = {
                        qty: qtyVal
                    };
                }
            }
        });

        let generalObservation = $('#general_observation').val().trim();

        Swal.fire({
            title: '¿Estás seguro?',
            text: "¿Deseas registrar esta lectura para la trampa externa seleccionada?",
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, guardar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                
                let payload = {
                    date_reading: dateReading,
                    trap_out_id: trapId,  // Clave específica para trampa externa
                    observation: generalObservation,
                    targets: targetsData
                };

                $.ajax({
                    url: window.location.pathname,
                    type: 'POST',
                    data: JSON.stringify(payload),
                    contentType: 'application/json',
                    headers: {
                        'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
                    },
                    success: function(response) {
                        if (response.hasOwnProperty('error')) {
                            Swal.fire('Error', response.error, 'error');
                            return;
                        }
                        
                        Swal.fire({
                            title: '¡Guardado!',
                            text: response.msg || 'Lectura guardada correctamente',
                            icon: 'success',
                            timer: 1500,
                            showConfirmButton: false
                        }).then(() => {
                            window.location.href = response.success_url || '.';
                        });
                    },
                    error: function() {
                        Swal.fire('Error', 'Ocurrió un error al enviar el formulario.', 'error');
                    }
                });

            }
        });
    });
});

// Función para cargar las trampas externas que no han sido leídas esta semana
function loadAvailableExternalTraps() {
    let trapSelect = $('#select_trap');
    trapSelect.empty().append('<option value="">--------- Cargando trampas externas ---------</option>');
    $('#matrix_container').hide();

    $.ajax({
        url: window.location.pathname,
        type: 'GET',
        data: {
            action: 'get_available_traps'
        },
        success: function(response) {
            trapSelect.empty().append('<option value="">--------- Seleccione una trampa externa---------</option>');
            if (response && response.length > 0) {
                $.each(response, function(index, trap) {
                    trapSelect.append(`<option value="${trap.id}">${trap.name}</option>`);
                });
                trapSelect.prop('disabled', false);
            } else {
                trapSelect.append('<option value="">No hay trampas externas disponibles para registrar esta semana</option>');
                trapSelect.prop('disabled', true);
            }
        },
        error: function() {
            trapSelect.empty().append('<option value="">Error al cargar las trampas externas</option>');
            alert("Error al cargar las trampas externas disponibles.");
        }
    });
}