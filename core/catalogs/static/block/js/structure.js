$(function () {

    function getStructureData() {

        return {
            code: $('#id_code').val(),
            name: $('#id_name').val(),
            bays: parseInt($('#id_bay_quantity').val()),
            beds: parseInt($('#id_bed_quantity').val()),
            sections: parseInt($('#id_section_quantity').val()),
            hasSides: $('#id_has_sides').is(':checked')
        };
    }

    function validateStructureData(data) {

        if (!data.code || !data.name) {

            Swal.fire({
                icon: 'warning',
                title: 'Datos incompletos',
                text: 'Ingrese el código y el nombre del bloque'
            });

            return false;
        }

        if (!data.bays || !data.beds || !data.sections) {

            Swal.fire({
                icon: 'warning',
                title: 'Cantidades incompletas',
                text: 'Ingrese naves, camas por nave y cuadros por cama'
            });

            return false;
        }

        if (data.bays < 1 || data.beds < 1 || data.sections < 1) {

            Swal.fire({
                icon: 'warning',
                title: 'Cantidades inválidas',
                text: 'Las cantidades deben ser mayores o iguales a 1'
            });

            return false;
        }

        return true;
    }

    $('.btnPreview').on('click', function () {

        let data = getStructureData();

        if (!validateStructureData(data)) {
            return;
        }

        let html = '';
        let totalBeds = data.bays * data.beds;
        let totalSections = totalBeds * data.sections;

        html += `
            <div class="card shadow-sm">
                <div class="card-header">
                    Vista previa
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-3 mb-2">
                            <div class="alert alert-light border mb-0 py-2">
                                <strong>${data.bays}</strong><br>
                                Naves
                            </div>
                        </div>
                        <div class="col-md-3 mb-2">
                            <div class="alert alert-light border mb-0 py-2">
                                <strong>${data.beds}</strong><br>
                                Camas por nave
                            </div>
                        </div>
                        <div class="col-md-3 mb-2">
                            <div class="alert alert-light border mb-0 py-2">
                                <strong>${data.sections}</strong><br>
                                Cuadros por cama
                            </div>
                        </div>
                        <div class="col-md-3 mb-2">
                            <div class="alert alert-light border mb-0 py-2">
                                <strong>${totalSections}</strong><br>
                                Cuadros totales
                            </div>
                        </div>
                    </div>

                    <div class="row">
        `;

        let middle = Math.floor(data.bays / 2);

        if (data.hasSides) {

            html += `
                <div class="col-md-6">

                    <h5>Lado A</h5>
            `;

            for (let i = 1; i <= middle; i++) {

                html += `
                    <div class="alert alert-success py-2">
                        <strong>Nave ${i}</strong>
                        <span class="float-end">${data.beds} camas / ${data.beds * data.sections} cuadros</span>
                    </div>
                `;
            }

            html += `
                </div>
                <div class="col-md-6">

                    <h5>Lado B</h5>
            `;

            for (let i = middle + 1; i <= data.bays; i++) {

                html += `
                    <div class="alert alert-info py-2">
                        <strong>Nave ${i}</strong>
                        <span class="float-end">${data.beds} camas / ${data.beds * data.sections} cuadros</span>
                    </div>
                `;
            }

            html += `
                </div>
            `;

        } else {

            html += `
                <div class="col-md-12">
            `;

            for (let i = 1; i <= data.bays; i++) {

                html += `
                    <div class="alert alert-secondary py-2">
                        <strong>Nave ${i}</strong>
                        <span class="float-end">${data.beds} camas / ${data.beds * data.sections} cuadros</span>
                    </div>
                `;
            }

            html += `
                </div>
            `;
        }

        html += `
                    </div>

                    <hr>

                    <button
                        type="button"
                        class="btn btn-success btnSave">

                        <i class="fas fa-save"></i>

                        Crear estructura

                    </button>

                </div>
            </div>
        `;

        $('#preview').html(html);

    });

    $(document).on('click', '.btnSave', function () {

        let data = getStructureData();

        if (!validateStructureData(data)) {
            return;
        }

        $.ajax({

            url: window.location.pathname,

            type: 'POST',

            headers: {
                'X-CSRFToken': csrftoken
            },

            data: {

                action: 'create',

                code: data.code,

                name: data.name,

                has_sides: data.hasSides,

                bay_quantity: data.bays,

                bed_quantity: data.beds,

                section_quantity: data.sections
            },

            success: function (response) {

                if (response.error) {

                    Swal.fire({
                        icon: 'error',
                        title: 'No se pudo crear',
                        text: response.error
                    });

                    return;
                }

                Swal.fire({
                    icon: 'success',
                    title: 'Estructura creada'
                });

                location.reload();
            }
        });

    });

});
