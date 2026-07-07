$('#frmForm').on('submit', function (e) {

    e.preventDefault();

    let formData = new FormData(this);

    $.ajax({
        url: window.location.href,
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,

        success: function (data) {

            if (data.success) {

                Swal.fire({
                    icon: 'success',
                    title: 'Importación exitosa',
                    text: 'El archivo fue cargado correctamente'
                }).then(() => {
                    window.location.href = list_url;
                });

            } else {

                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'Error desconocido'
                });
            }
        },

        error: function (xhr) {

            console.log(xhr.responseText);

            Swal.fire({
                icon: 'error',
                title: 'Error del servidor',
                text: 'Revisa consola'
            });
        }
    });
});