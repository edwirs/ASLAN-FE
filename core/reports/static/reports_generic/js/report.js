// Reporte genérico: filtros + tarjetas KPI + gráfico + tabla exportable, todo definido por la configuración
// que entrega la vista (#report-config) y los datos que responde el POST "search_report".
//
// Columnas (config de la vista):  key, title, type (text|number|money|percent|badge), y opcionales:
//   detail   -> no va en la tabla: se ve al desplegar la fila (y se incluye al exportar)
//   sub      -> clave de otro campo que se muestra como texto pequeño debajo del valor
//   tag      -> clave de otro campo que se muestra como etiqueta junto al valor
//   bar      -> (percent) dibuja una barra de fondo proporcional
//   small / bold, colors (badge), showWhen: [filtro, valor]
var reportCfg, dateStart = null, dateEnd = null, tblReport = null, lastColumns = [], lastChart = null;

function esc(t) {
    return $('<div>').text(t === null || t === undefined ? '' : t).html();
}

function fmt(value, type) {
    if (value === '' || value === null || value === undefined) return '';
    var n = parseFloat(value);
    if (type === 'money') return '$ ' + n.toLocaleString('es-CO', {maximumFractionDigits: 0});
    if (type === 'percent') return n.toLocaleString('es-CO', {maximumFractionDigits: 1}) + '%';
    if (type === 'number') return n.toLocaleString('es-CO', {maximumFractionDigits: 2});
    return esc(value);
}

function renderFilters() {
    var html = '';
    reportCfg.filters.forEach(function (f) {
        var id = 'f_' + f.name;
        var field = '';
        var wide = f.type === 'daterange' ? ' f-wide' : '';
        if (f.type === 'daterange') {
            field = '<div class="input-group"><span class="input-group-text"><i class="fas fa-calendar-alt"></i></span>' +
                '<input type="text" class="form-control rpt-date" id="' + id + '" autocomplete="off" readonly></div>';
        } else if (f.type === 'select') {
            field = '<select class="form-select" id="' + id + '">' + f.options.map(function (o) {
                return '<option value="' + esc(o.value) + '">' + esc(o.label) + '</option>';
            }).join('') + '</select>';
        } else if (f.type === 'number') {
            field = '<input type="number" min="1" class="form-control" id="' + id + '" value="' + (f.default || '') + '">';
        } else if (f.type === 'checkbox') {
            field = '<div class="f-check form-check form-switch"><input class="form-check-input" type="checkbox" role="switch" id="' + id + '"' + (f.default ? ' checked' : '') + '>' +
                '<label class="form-check-label" for="' + id + '">' + esc(f.label) + '</label></div>';
            html += '<div>' + '<label class="f-label">&nbsp;</label>' + field + '</div>';
            return;
        }
        html += '<div class="' + wide.trim() + '"><label class="f-label" for="' + id + '">' + esc(f.label) + '</label>' + field + '</div>';
    });
    html += '<div><label class="f-label">&nbsp;</label><button type="button" class="btn btn-primary w-100" id="btn_run"><i class="fas fa-sync-alt"></i> Actualizar</button></div>';
    $('#report_filters').html(html);

    reportCfg.filters.filter(function (f) { return f.type === 'daterange'; }).forEach(function (f) {
        var $in = $('#f_' + f.name);
        var ranges = {
            'Hoy': [moment(), moment()],
            'Últimos 7 días': [moment().subtract(6, 'days'), moment()],
            'Este mes': [moment().startOf('month'), moment().endOf('month')],
            'Mes pasado': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')],
            'Este año': [moment().startOf('year'), moment()],
            'Todo el historial': [moment('2000-01-01'), moment()]
        };
        $in.daterangepicker({
            autoApply: true, ranges: ranges, alwaysShowCalendars: true, opens: 'right',
            startDate: moment().startOf('month'), endDate: moment().endOf('month'),
            locale: {format: 'DD/MM/YYYY'}
        }).on('apply.daterangepicker', function (e, picker) {
            if (picker.chosenLabel === 'Todo el historial') {
                dateStart = dateEnd = '';
                $in.val('Todo el historial');
            } else {
                dateStart = picker.startDate.format('YYYY-MM-DD');
                dateEnd = picker.endDate.format('YYYY-MM-DD');
            }
            run();
        });
        dateStart = moment().startOf('month').format('YYYY-MM-DD');
        dateEnd = moment().endOf('month').format('YYYY-MM-DD');
    });
    $('#report_filters select, #report_filters input[type="checkbox"], #report_filters input[type="number"]').on('change', function () {
        run();
    });
}

function collectParams() {
    var params = {action: 'search_report'};
    reportCfg.filters.forEach(function (f) {
        var $el = $('#f_' + f.name);
        if (f.type === 'daterange') {
            params.start_date = dateStart || '';
            params.end_date = dateEnd || '';
        } else if (f.type === 'checkbox') {
            if ($el.is(':checked')) params[f.name] = 'on';
        } else {
            params[f.name] = $el.val();
        }
    });
    return params;
}

function visibleColumns(columns) {
    return columns.filter(function (c) {
        if (!c.showWhen) return true;
        return $('#f_' + c.showWhen[0]).val() === c.showWhen[1];
    });
}

// Valor formateado de una celda para mostrar (tabla o detalle desplegable)
function displayValue(c, row) {
    var data = row[c.key];
    if (data === '' || data === null || data === undefined) return '';
    if (c.type === 'badge') {
        var color = (c.colors || {})[data] || 'secondary';
        return '<span class="badge bg-' + color + (color === 'light' ? ' text-dark' : '') + '">' + esc(data) + '</span>';
    }
    if (c.type === 'text') {
        var t = esc(data);
        if (c.bold) t = '<b>' + t + '</b>';
        if (c.tag && row[c.tag]) t += ' <span class="badge bg-info">' + esc(row[c.tag]) + '</span>';
        if (c.sub && row[c.sub]) t += '<span class="cell-sub">' + esc(row[c.sub]) + '</span>';
        return c.small ? '<span class="cell-sub">' + t + '</span>' : t;
    }
    if (c.type === 'percent' && c.bar) {
        var w = Math.max(0, Math.min(100, parseFloat(data)));
        return '<div class="pbar"><span style="width:' + w + '%"></span><b>' + fmt(data, 'percent') + '</b></div>';
    }
    var cls = parseFloat(data) < 0 ? ' class="cell-neg"' : '';
    return '<span' + cls + '>' + fmt(data, c.type) + '</span>';
}

function cellRenderer(c) {
    return function (data, type, row) {
        if (type === 'export') {
            if (c.type === 'money' || c.type === 'number' || c.type === 'percent') {
                return data === '' || data === null ? '' : parseFloat(data);
            }
            var txt = data === null || data === undefined ? '' : String(data);
            if (c.tag && row[c.tag]) txt += ' (' + row[c.tag] + ')';
            return txt;
        }
        if (type !== 'display') return data;
        return displayValue(c, row);
    };
}

function renderKpis(kpis) {
    $('#report_kpis').html((kpis || []).map(function (k) {
        var neg = parseFloat(k.value) < 0 ? ' kpi-neg' : '';
        return '<div class="kpi-card' + neg + '"><div class="kpi-label">' + esc(k.label) + '</div>' +
            '<div class="kpi-value">' + fmt(k.value, k.type) + '</div></div>';
    }).join(''));
}

// Colores del gráfico según el tema (claro u oscuro)
function chartTheme() {
    var dark = window.AslanTheme && window.AslanTheme.isDark();
    var text = dark ? '#ced4da' : '#333333';
    return {
        chart: {backgroundColor: 'transparent'},
        colors: dark ? ['#6cb2eb', '#f6ad55', '#68d391', '#fc8181', '#b794f4', '#f687b3'] : undefined,
        title: {style: {color: dark ? '#f8f9fa' : '#333333'}},
        xAxis: {labels: {style: {color: text}}, lineColor: dark ? '#6c757d' : '#ccd6eb', tickColor: dark ? '#6c757d' : '#ccd6eb'},
        yAxis: {labels: {style: {color: text}}, gridLineColor: dark ? '#4b545c' : '#e6e6e6'},
        legend: {itemStyle: {color: text}, itemHoverStyle: {color: dark ? '#fff' : '#000'}}
    };
}

function renderChart(chart) {
    lastChart = chart;
    var $box = $('#report_chart');
    if (!chart || !chart.categories.length) {
        $box.hide().empty();
        return;
    }
    $box.show();
    var dual = !!chart.dual;
    var horizontal = chart.series.every(function (s) { return s.type === 'bar'; });
    var theme = chartTheme();
    Highcharts.chart('report_chart', {
        chart: {type: horizontal ? 'bar' : 'column', backgroundColor: theme.chart.backgroundColor,
            height: horizontal ? Math.max(260, chart.categories.length * 34 + 90) : 340},
        title: {text: chart.title, style: {fontSize: '15px', color: theme.title.style.color}},
        xAxis: {categories: chart.categories, labels: {style: {fontSize: '11px', color: theme.xAxis.labels.style.color}},
            lineColor: theme.xAxis.lineColor, tickColor: theme.xAxis.tickColor},
        yAxis: dual ? [
            {title: {text: null}, min: 0, labels: theme.yAxis.labels, gridLineColor: theme.yAxis.gridLineColor},
            {title: {text: null}, opposite: true, min: 0, max: 100, labels: {format: '{value}%', style: theme.yAxis.labels.style}}
        ] : {title: {text: null}, min: 0, labels: theme.yAxis.labels, gridLineColor: theme.yAxis.gridLineColor},
        legend: theme.legend,
        colors: theme.colors,
        tooltip: {shared: true},
        credits: {enabled: false},
        series: chart.series.map(function (s) {
            return {
                name: s.name, type: s.type === 'bar' ? undefined : s.type, data: s.data, yAxis: s.yAxis || 0,
                tooltip: s.money ? {valuePrefix: '$ '} : (s.suffix ? {valueSuffix: s.suffix} : {})
            };
        })
    });
}

function renderSummary(summary) {
    var $box = $('#report_summary');
    if (!summary || !summary.rows.length) {
        $box.hide().empty();
        return;
    }
    var head = summary.columns.map(function (c) { return '<th>' + esc(c.title) + '</th>'; }).join('');
    var body = summary.rows.map(function (r) {
        return '<tr>' + summary.columns.map(function (c) { return '<td>' + displayValue(c, r) + '</td>'; }).join('') + '</tr>';
    }).join('');
    $box.html('<h6 class="fw-bold">' + esc(summary.title) + '</h6><div class="table-responsive"><table class="table table-sm table-striped"><thead><tr>' +
        head + '</tr></thead><tbody>' + body + '</tbody></table></div>').show();
}

function detailHtml(row, detailCols) {
    var items = detailCols.map(function (c) {
        var v = displayValue(c, row);
        if (v === '' || v === null) return '';
        return '<div><span class="dl">' + esc(c.title) + '</span><span class="dv">' + v.replace('cell-sub', 'cell-plain') + '</span></div>';
    }).join('');
    return '<div class="row-detail">' + items + '</div>';
}

function renderTable(rows, allColumns) {
    var columns = visibleColumns(allColumns);
    var main = columns.filter(function (c) { return !c.detail; });
    var detail = columns.filter(function (c) { return c.detail; });
    var ordered = main.concat(detail);
    var hasDetail = detail.length > 0;
    var offset = hasDetail ? 1 : 0;
    lastColumns = ordered;

    if (tblReport) {
        $('#tblReport tbody').off('click');
        tblReport.destroy();
        $('#tblReport').empty().append('<thead></thead><tbody></tbody>');
    }
    $('#tblReport thead').html('<tr>' + (hasDetail ? '<th></th>' : '') + main.map(function (c) { return '<th>' + esc(c.title) + '</th>'; }).join('') +
        detail.map(function (c) { return '<th>' + esc(c.title) + '</th>'; }).join('') + '</tr>');

    var dtColumns = [];
    if (hasDetail) {
        dtColumns.push({data: null, orderable: false, className: 'ctl', defaultContent: '<i class="fas fa-chevron-right"></i>'});
    }
    ordered.forEach(function (c, i) {
        dtColumns.push({
            data: c.key, render: cellRenderer(c), visible: !c.detail,
            className: c.type === 'text' || c.type === 'badge' ? '' : 'text-end'
        });
    });
    var exportCols = ordered.map(function (c, i) { return i + offset; });
    var title = reportCfg.title + ' - ' + moment().format('YYYY-MM-DD');
    tblReport = $('#tblReport').DataTable({
        autoWidth: false,
        data: rows,
        order: [],
        pageLength: 15,
        lengthMenu: [[15, 25, 50, 100, -1], [15, 25, 50, 100, 'Todos']],
        dom: "<'row align-items-center mb-2'<'col-sm-6'B><'col-sm-6'f>>rt<'row mt-2'<'col-md-4'i><'col-md-4 text-center'l><'col-md-4'p>>",
        buttons: [
            {extend: 'excelHtml5', text: '<i class="fas fa-file-excel"></i> Excel', className: 'btn btn-success btn-sm', title: title,
                filename: reportCfg.export_name, exportOptions: {columns: exportCols, orthogonal: 'export'}},
            {extend: 'pdfHtml5', text: '<i class="fas fa-file-pdf"></i> PDF', className: 'btn btn-danger btn-sm', title: title,
                filename: reportCfg.export_name, orientation: 'landscape', pageSize: 'A4',
                exportOptions: {columns: exportCols, orthogonal: 'export'},
                customize: function (doc) { doc.defaultStyle.fontSize = 7; doc.styles.tableHeader.fontSize = 7; }}
        ],
        columns: dtColumns,
        createdRow: function (tr) {
            if (hasDetail) $(tr).addClass('has-detail');
        }
    });

    if (hasDetail) {
        $('#tblReport tbody').on('click', 'tr.has-detail', function (e) {
            if ($(e.target).closest('a, button, input').length) return;
            var row = tblReport.row(this);
            if (row.child.isShown()) {
                row.child.hide();
                $(this).removeClass('shown');
            } else {
                row.child(detailHtml(row.data(), detail)).show();
                $(this).addClass('shown');
            }
        });
    }
    $('#table_hint').toggle(hasDetail && rows.length > 0);
}

function run() {
    var params = collectParams();
    $('#report_status').text('Consultando...');
    $.ajax({
        url: pathname,
        type: 'POST',
        headers: {'X-CSRFToken': csrftoken},
        data: params,
        success: function (response) {
            if (response.error) {
                $('#report_status').text('');
                return message_error(response.error);
            }
            if (!response.columns) {
                $('#report_status').text('');
                return message_error('La respuesta del reporte no es válida. Recargue la página.');
            }
            renderKpis(response.kpis);
            renderChart(response.chart);
            renderSummary(response.summary);
            renderTable(response.rows, response.columns);
            var notes = response.notes || [];
            $('#report_notes').html(notes.map(function (n) { return '<div><i class="fas fa-info-circle"></i> ' + esc(n) + '</div>'; }).join('')).toggle(notes.length > 0);
            $('#report_status').text('(' + response.rows.length + ' registro' + (response.rows.length === 1 ? '' : 's') + ')');
        },
        error: function (xhr) {
            $('#report_status').text('');
            message_error(xhr.status === 403 ? 'Su perfil no tiene permiso para este reporte.' : 'No se pudo consultar el reporte.');
        }
    });
}

// Al cambiar de tema se vuelve a dibujar el gráfico con los colores nuevos
document.addEventListener('themechange', function () {
    if (lastChart) renderChart(lastChart);
});

$(function () {
    reportCfg = JSON.parse($('#report-config').text());
    $('#table_title').text(reportCfg.table_title || 'Detalle');
    renderFilters();
    $('#btn_run').on('click', run);
    run();
});
