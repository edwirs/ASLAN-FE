// create.js

document.addEventListener("DOMContentLoaded", function() {
    console.log("¡El archivo JS externo de la matriz por tarjetas cargó correctamente!");

    // 1. Evento cuando cambia el Bloque
    $('#select_block').on('change', function() {
        let blockId = $(this).val();
        let trapSelect = $('#select_trap');
        
        trapSelect.empty().append('<option value="">--------- Seleccione una trampa ---------</option>');
        $('#matrix_container').hide();

        if (!blockId) {
            trapSelect.prop('disabled', true);
            return;
        }

        $.ajax({
            url: window.location.pathname,
            type: 'GET',
            data: {
                action: 'get_traps_by_block',
                block_id: blockId
            },
            success: function(response) {
                if (response && response.length > 0) {
                    $.each(response, function(index, trap) {
                        trapSelect.append(`<option value="${trap.id}">${trap.name}</option>`);
                    });
                    trapSelect.prop('disabled', false);
                } else {
                    trapSelect.append('<option value="">No hay trampas activas en este bloque</option>');
                    trapSelect.prop('disabled', true);
                }
            },
            error: function() {
                alert("Error al cargar las trampas del bloque.");
            }
        });
    });

    // 2. Evento cuando selecciona una Trampa específica
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
        let container = btn.closest('.input-controls-row'); // <-- Actualizado aquí
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
            Swal.fire('Error', 'Por favor seleccione un bloque y una trampa.', 'warning');
            return;
        }

        // Recolectamos cantidades y observaciones recorriendo las tarjetas
        let targetsData = {};
        
        $('.input-qty').each(function() {
            let inputQty = $(this);
            let inputName = inputQty.attr('name'); // qty_{target_id}
            let parts = inputName.split('_');
            
            if (parts.length === 2) {
                let targetId = parts[1];
                let qtyVal = parseInt(inputQty.val()) || 0;
                
                // Buscamos su respectivo input de observación en la misma tarjeta
                let obsInput = $(`input[name="obs_${targetId}"]`);
                let obsVal = obsInput.length ? obsInput.val().trim() : '';

                // Guardamos si tiene cantidad o si escribieron una observación
                if (qtyVal > 0 || obsVal !== '') {
                    targetsData[targetId] = {
                        qty: qtyVal
                    };
                }
            }
        });

        let generalObservation = $('#general_observation').val().trim();

        Swal.fire({
            title: '¿Estás seguro?',
            text: "¿Deseas registrar esta lectura para la trampa seleccionada?",
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, guardar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                
                let payload = {
                    date_reading: dateReading,
                    trap_in_id: trapId,
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