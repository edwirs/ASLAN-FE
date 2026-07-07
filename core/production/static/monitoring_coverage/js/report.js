$.fn.dataTable.ext.errMode = 'none'; // Silencia errores de tablas que no existen

$(function () {
    // 1. Función para obtener el token CSRF de las cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // 2. Configurar AJAX global
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });

    // 3. Inicializar DateRangePicker
    $('input[name="date_range"]').daterangepicker({
        language: 'es',
        startDate: new Date(),
        endDate: new Date(),
        locale: {
            format: 'DD/MM/YYYY',
            applyLabel: 'Aplicar',
            cancelLabel: 'Cancelar',
        }
    });

    // 4. Función para cargar datos
    function get_graph_data() {
        var date_range = $('input[name="date_range"]').val();
        
        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            data: {
                'action': 'get_graph_data',
                'date_range': date_range
            },
            dataType: 'json',
            success: function (data) {
                render_chart(data);
            },
            error: function (xhr, status, error) {
                console.error("Error al cargar datos:", error);
            }
        });
    }

    // 5. Renderizar gráfico con etiquetas de porcentaje
    function render_chart(data) {
        Highcharts.chart('graph_container', {
            chart: { type: 'column', borderRadius: 8 },
            title: { text: null },
            xAxis: { categories: data.categories },
            yAxis: {
                min: 0,
                title: { text: 'Cantidad de Camas' }
            },
            tooltip: {
                shared: true,
                pointFormat: '{series.name}: <b>{point.y}</b><br/>'
            },
            plotOptions: {
                column: { 
                    pointPadding: 0.2, 
                    borderWidth: 0, 
                    borderRadius: 5,
                    dataLabels: {
                        enabled: true,
                        formatter: function() {
                            // Solo etiquetamos la serie de "Monitoreado" (índice 1)
                            if (this.series.index === 1) {
                                // Obtenemos la meta (índice 0) para deducir el total
                                // Meta = 50% del total, por tanto Total = Meta * 2
                                let meta = this.series.chart.series[0].data[this.point.index].y;
                                let totalCamas = meta * 2;
                                
                                if (totalCamas > 0) {
                                    let percent = (this.y / totalCamas) * 100;
                                    return Math.round(percent) + '%';
                                }
                            }
                            return null;
                        },
                        style: {
                            fontWeight: 'bold',
                            color: '#000000',
                            textOutline: '1px contrast'
                        }
                    }
                }
            },
            series: [{
                name: 'Meta (50%)',
                data: data.target_data,
                color: '#cbd5e1'
            }, {
                name: 'Monitoreado',
                data: data.real_data,
                color: '#f97316'
            }]
        });
    }

    // 6. Evento botón
    $('#btnSearch').on('click', function () {
        get_graph_data();
    });

    // Carga inicial
    get_graph_data();
});