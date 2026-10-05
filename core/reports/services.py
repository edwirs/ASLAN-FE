"""Cálculo de los reportes de ventas por producto e inventario.

Cada función recibe los filtros (``params``, un dict de cadenas) y si el usuario puede ver costos
(``can_costs``). Devuelven ``{'kpis', 'rows', 'chart', 'summary', 'notes'}``. Los datos de costo,
utilidad y valor de inventario SOLO se incluyen si ``can_costs``: se omiten aquí, en el servidor,
no se ocultan en el navegador.
"""
import math
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.db.models import Max

from core.pos.models import BuyDetail, CreditNoteDetail, Product, SaleDetail


# --------------------------------------------------------------------------- utilidades
def _date(value):
    value = (value or '').strip()
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None


def _int(value, default, minimum=1, maximum=3650):
    try:
        return min(max(int(value), minimum), maximum)
    except (TypeError, ValueError):
        return default


def _f(value):
    return float(value) if value is not None else 0.0


def _round(value, digits=2):
    return round(value, digits)


def _active_products(params, include_inactive=False):
    qs = Product.objects.filter(is_service=False).select_related('category').prefetch_related('presentations')
    if not include_inactive:
        qs = qs.filter(is_active=True)
    if params.get('category'):
        qs = qs.filter(category_id=params['category'])
    return qs


def holders_of(product):
    """Unidades de stock del producto: una por cada lugar donde se guarda stock.

    Devuelve dicts con ``key`` (clave del stock), ``label`` (variante o unidad), ``stock``, ``cost``
    (costo de la unidad de ese stock), ``pvp`` y ``min`` (stock mínimo aplicable).
    """
    min_stock = _f(product.min_stock) if product.min_stock is not None else None
    if product.has_own_stock_variants():
        holders = [{'key': ('b', product.pk), 'label': product.unit_name or 'Unidad', 'stock': _f(product.stock),
                    'cost': _f(product.price), 'pvp': _f(product.pvp), 'min': min_stock}]
        for p in sorted((p for p in product.presentations.all() if p.is_active), key=lambda p: p.id):
            holders.append({'key': ('p', p.pk), 'label': p.name, 'stock': _f(p.stock),
                            'cost': _f(p.price), 'pvp': _f(p.pvp), 'min': min_stock})
        return holders
    return [{'key': ('b', product.pk), 'label': product.unit_name or 'Unidad', 'stock': _f(product.stock),
             'cost': _f(product.price), 'pvp': _f(product.pvp), 'min': min_stock}]


def equivalences(product):
    """Texto 'Caja x24: 4 · Six pack: 19' con cuántas de cada presentación caben (solo conversión)."""
    if product.has_own_stock_variants() or not product.uses_presentations:
        return ''
    items = sorted((p for p in product.presentations.all() if p.is_active), key=lambda p: (-p.factor, p.id))
    return ' · '.join(f'{p.name}: {int(product.stock // p.factor)}' for p in items if p.factor)


def _state(stock, minimum):
    if stock <= 0:
        return 'Agotado'
    if minimum is not None and stock <= minimum:
        return 'Bajo'
    return 'Normal'


def _holder_key(detail):
    """A qué stock descontó una línea de venta."""
    if detail['own_stock'] and detail['presentation_id']:
        return ('p', detail['presentation_id'])
    return ('b', detail['product_id'])


def _sale_lines(start=None, end=None, **filters):
    qs = SaleDetail.objects.filter(is_active=True, sale__is_active=True)
    if start:
        qs = qs.filter(sale__date_joined__gte=start)
    if end:
        qs = qs.filter(sale__date_joined__lte=end)
    if filters.get('category'):
        qs = qs.filter(product__category_id=filters['category'])
    if filters.get('employee'):
        qs = qs.filter(sale__employee_id=filters['employee'])
    if filters.get('electronic') == 'yes':
        qs = qs.filter(sale__is_electronicinvoice=True)
    elif filters.get('electronic') == 'no':
        qs = qs.filter(sale__is_electronicinvoice=False)
    return qs


# --------------------------------------------------------------------------- ventas por producto
def sales_by_product(params, can_costs):
    start, end = _date(params.get('start_date')), _date(params.get('end_date'))
    group = params.get('group') or 'product'
    filters = {k: params.get(k) for k in ('category', 'employee', 'electronic')}

    rows = {}
    estimated_cost_lines = total_lines = 0

    def row_for(product_id, name, code, category, label):
        key = (product_id, label if group == 'presentation' else '')
        return rows.setdefault(key, {
            'product_id': product_id, 'code': code, 'name': name, 'category': category,
            'presentation': label if group == 'presentation' else '', 'breakdown': defaultdict(float),
            'sales': set(), 'qty': 0.0, 'units': 0.0, 'revenue': 0.0, 'cost': 0.0,
            'ret_qty': 0.0, 'ret_amount': 0.0, 'ret_cost': 0.0,
        })

    lines = _sale_lines(start, end, **filters).values(
        'product_id', 'product__name', 'product__code', 'product__category__name', 'presentation_name',
        'factor', 'cant', 'total', 'cost', 'product__price', 'sale_id')
    for d in lines:
        label = d['presentation_name'] or ''
        r = row_for(d['product_id'], d['product__name'], d['product__code'], d['product__category__name'], label)
        cant, factor = d['cant'], _f(d['factor'])
        r['qty'] += cant
        r['units'] += cant * factor
        r['revenue'] += _f(d['total'])
        r['sales'].add(d['sale_id'])
        r['breakdown'][label or 'Unidad'] += cant
        total_lines += 1
        if d['cost'] is not None:
            r['cost'] += _f(d['cost']) * cant
        else:
            # Venta anterior al costo guardado: se estima con el costo actual del producto
            r['cost'] += _f(d['product__price']) * factor * cant
            estimated_cost_lines += 1

    if filters.get('electronic') != 'no':
        credit_qs = CreditNoteDetail.objects.filter(credit_note__isnull=False)
        if start:
            credit_qs = credit_qs.filter(credit_note__date_joined__gte=start)
        if end:
            credit_qs = credit_qs.filter(credit_note__date_joined__lte=end)
        if filters.get('category'):
            credit_qs = credit_qs.filter(product__category_id=filters['category'])
        if filters.get('employee'):
            credit_qs = credit_qs.filter(credit_note__employee_id=filters['employee'])
        for d in credit_qs.values('product_id', 'product__name', 'product__code', 'product__category__name',
                                  'cant', 'total', 'sale_detail__presentation_name', 'sale_detail__cost',
                                  'sale_detail__factor', 'product__price'):
            label = d['sale_detail__presentation_name'] or ''
            r = row_for(d['product_id'], d['product__name'], d['product__code'], d['product__category__name'], label)
            r['ret_qty'] += d['cant']
            r['ret_amount'] += _f(d['total'])
            unit_cost = d['sale_detail__cost'] if d['sale_detail__cost'] is not None else (
                _f(d['product__price']) * (_f(d['sale_detail__factor']) or 1))
            r['ret_cost'] += _f(unit_cost) * d['cant']

    products = {p.pk: p for p in Product.objects.filter(pk__in={k[0] for k in rows}).prefetch_related('presentations')}
    result = []
    for r in rows.values():
        net_sales = r['revenue'] - r['ret_amount']
        net_cost = r['cost'] - r['ret_cost']
        net_qty = r['qty'] - r['ret_qty']
        product = products.get(r['product_id'])
        stock_text = ''
        if product is not None:
            summary = product.stock_summary()
            if summary['mode'] == 'service':
                stock_text = 'Sin inventario'
            elif summary['mode'] == 'variants':
                stock_text = ' · '.join(f"{i['name']}: {i['stock']:g}" for i in summary['items'])
            else:
                stock_text = f"{summary['total']:g} {summary['unit']}"
        item = {
            'code': r['code'], 'name': r['name'], 'category': r['category'], 'presentation': r['presentation'],
            'breakdown': ' · '.join(f'{k}: {v:g}' for k, v in sorted(r['breakdown'].items(), key=lambda kv: -kv[1])),
            'qty': _round(r['qty'], 3), 'ret_qty': _round(r['ret_qty'], 3), 'net_qty': _round(net_qty, 3),
            'units': _round(r['units'], 3), 'sales_count': len(r['sales']),
            'revenue': _round(r['revenue']), 'ret_amount': _round(r['ret_amount']), 'net_sales': _round(net_sales),
            'avg_price': _round(net_sales / net_qty) if net_qty else 0, 'stock': stock_text,
        }
        if can_costs:
            # Sin costo registrado (p. ej. servicios) no se inventa una utilidad del 100%
            if net_cost > 0:
                item.update({'cost': _round(net_cost), 'profit': _round(net_sales - net_cost),
                             'margin': _round((net_sales - net_cost) / net_sales * 100, 1) if net_sales else 0})
            else:
                item.update({'cost': '', 'profit': '', 'margin': ''})
        result.append(item)

    total_sales = sum(i['net_sales'] for i in result)
    for i in result:
        i['share'] = _round(i['net_sales'] / total_sales * 100, 1) if total_sales else 0
    result.sort(key=lambda i: -i['net_sales'])

    kpis = [
        {'label': 'Ventas netas', 'value': _round(total_sales), 'type': 'money'},
        {'label': 'Devoluciones (notas crédito)', 'value': _round(sum(i['ret_amount'] for i in result)), 'type': 'money'},
        {'label': 'Productos vendidos', 'value': len({i['code'] for i in result}), 'type': 'number'},
    ]
    notes = []
    if can_costs:
        with_cost = [i for i in result if i['cost'] != '']
        sales_with_cost = sum(i['net_sales'] for i in with_cost)
        profit = sales_with_cost - sum(i['cost'] for i in with_cost)
        kpis[1:1] = [
            {'label': 'Utilidad', 'value': _round(profit), 'type': 'money'},
            {'label': 'Margen', 'value': _round(profit / sales_with_cost * 100, 1) if sales_with_cost else 0, 'type': 'percent'},
        ]
        no_cost = len(result) - len(with_cost)
        if no_cost:
            notes.append(f'{no_cost} producto(s) no tienen costo registrado (precio de compra en 0): no entran en la utilidad ni en el margen.')
        if estimated_cost_lines:
            notes.append(f'{estimated_cost_lines} de {total_lines} líneas vendidas son anteriores al costo guardado en la '
                         'venta: su costo se estima con el costo actual del producto.')
    notes.append('Ventas sin IVA, con el descuento de cada línea aplicado (no incluye descuentos globales de la factura).')

    top = result[:10]
    chart = {'title': 'Top 10 por ventas netas', 'categories': [i['name'] + (f" ({i['presentation']})" if i['presentation'] else '') for i in top],
             'series': [{'name': 'Ventas netas', 'type': 'bar', 'data': [i['net_sales'] for i in top], 'money': True}]}
    if can_costs:
        chart['series'].append({'name': 'Utilidad', 'type': 'bar', 'data': [i['profit'] if i['profit'] != '' else 0 for i in top], 'money': True})
    return {'kpis': kpis, 'rows': result, 'chart': chart, 'summary': None, 'notes': notes}


# --------------------------------------------------------------------------- inventario valorizado
def inventory_value(params, can_costs):
    state_filter = params.get('state') or ''
    rows = []
    for product in _active_products(params, include_inactive=params.get('inactive') == 'on'):
        eq = equivalences(product)
        for h in holders_of(product):
            state = _state(h['stock'], h['min'])
            if state_filter and state != state_filter:
                continue
            item = {
                'code': product.code, 'name': product.name, 'category': product.category.name, 'variant': h['label'],
                'stock': _round(h['stock'], 2), 'min': h['min'] if h['min'] is not None else '', 'state': state,
                'pvp': _round(h['pvp']), 'equivalences': eq if h['key'][0] == 'b' else '',
            }
            if can_costs:
                item.update({'cost_unit': _round(h['cost']), 'value_cost': _round(h['stock'] * h['cost']),
                             'value_sale': _round(h['stock'] * h['pvp']),
                             'potential': _round(h['stock'] * (h['pvp'] - h['cost']))})
            rows.append(item)
    rows.sort(key=lambda i: (i['category'], i['name'], i['variant']))

    kpis = [
        {'label': 'Referencias en inventario', 'value': len(rows), 'type': 'number'},
        {'label': 'Agotados', 'value': sum(1 for i in rows if i['state'] == 'Agotado'), 'type': 'number'},
        {'label': 'Con stock bajo', 'value': sum(1 for i in rows if i['state'] == 'Bajo'), 'type': 'number'},
    ]
    summary = chart = None
    if can_costs:
        kpis[1:1] = [
            {'label': 'Valor a costo', 'value': _round(sum(i['value_cost'] for i in rows)), 'type': 'money'},
            {'label': 'Valor a precio de venta', 'value': _round(sum(i['value_sale'] for i in rows)), 'type': 'money'},
            {'label': 'Utilidad potencial', 'value': _round(sum(i['potential'] for i in rows)), 'type': 'money'},
        ]
        by_cat = defaultdict(lambda: {'items': 0, 'value_cost': 0.0, 'value_sale': 0.0, 'potential': 0.0})
        for i in rows:
            c = by_cat[i['category']]
            c['items'] += 1
            c['value_cost'] += i['value_cost']
            c['value_sale'] += i['value_sale']
            c['potential'] += i['potential']
        cats = sorted(by_cat.items(), key=lambda kv: -kv[1]['value_cost'])
        summary = {'title': 'Valor del inventario por categoría', 'columns': [
            {'key': 'category', 'title': 'Categoría', 'type': 'text'},
            {'key': 'items', 'title': 'Referencias', 'type': 'number'},
            {'key': 'value_cost', 'title': 'Valor a costo', 'type': 'money'},
            {'key': 'value_sale', 'title': 'Valor a venta', 'type': 'money'},
            {'key': 'potential', 'title': 'Utilidad potencial', 'type': 'money'},
        ], 'rows': [dict(category=k, items=v['items'], value_cost=_round(v['value_cost']),
                         value_sale=_round(v['value_sale']), potential=_round(v['potential'])) for k, v in cats]}
        chart = {'title': 'Valor del inventario a costo por categoría', 'categories': [k for k, _ in cats[:10]],
                 'series': [{'name': 'Valor a costo', 'type': 'bar', 'data': [_round(v['value_cost']) for _, v in cats[:10]], 'money': True}]}
    notes = ['El valor a precio de venta usa el precio de la unidad (o de cada variante). Las presentaciones de un mismo '
             'stock (caja, six pack) no se suman: el stock se cuenta una sola vez, en la unidad base.']
    return {'kpis': kpis, 'rows': rows, 'chart': chart, 'summary': summary, 'notes': notes}


# --------------------------------------------------------------------------- reposición sugerida
def restock(params, can_costs):
    days = _int(params.get('days'), 30)
    cover = _int(params.get('cover'), 15)
    only_needed = params.get('only_needed') == 'on'
    today = date.today()
    since = today - timedelta(days=days - 1)

    demand = defaultdict(float)
    for d in _sale_lines(since, today, category=params.get('category')).values(
            'product_id', 'presentation_id', 'own_stock', 'cant', 'factor'):
        demand[_holder_key(d)] += d['cant'] * _f(d['factor'])

    last_buy = {}
    for b in BuyDetail.objects.select_related('buy_id__provider').order_by('-buy_id__date_joined', '-id').values(
            'product_id', 'presentation_name', 'price', 'buy_id__date_joined', 'buy_id__provider__names'):
        last_buy.setdefault(b['product_id'], b)

    rows = []
    for product in _active_products(params):
        presentations = []
        if product.uses_presentations and not product.has_own_stock_variants():
            presentations = sorted((p for p in product.presentations.all() if p.is_active), key=lambda p: -p.factor)
        for h in holders_of(product):
            sold = demand.get(h['key'], 0.0)
            minimum = h['min'] or 0.0
            if not sold and (h['min'] is None or h['stock'] > minimum):
                continue  # sin ventas en el período y sin alerta de mínimo: no hay nada que decidir
            avg = sold / days
            coverage = h['stock'] / avg if avg > 0 else None
            suggested = max(avg * cover - h['stock'], minimum - h['stock'] if h['min'] is not None else 0, 0)
            suggested = math.ceil(suggested - 1e-9)
            if h['stock'] <= 0 and (sold or h['min'] is not None):
                priority = 'Crítico'
            elif coverage is not None and coverage < 3:
                priority = 'Urgente'
            elif suggested > 0:
                priority = 'Pronto'
            else:
                priority = 'Cubierto'
            if only_needed and suggested <= 0:
                continue
            text = f'{suggested:g} {h["label"]}' if suggested else '-'
            for p in presentations:
                if suggested and p.factor and suggested >= float(p.factor):
                    text = f'{math.ceil(suggested / float(p.factor))} × {p.name} ({suggested:g} {h["label"]})'
                    break
            item = {
                'code': product.code, 'name': product.name, 'category': product.category.name, 'variant': h['label'],
                'stock': _round(h['stock'], 2), 'min': h['min'] if h['min'] is not None else '',
                'sold': _round(sold, 2), 'avg_daily': _round(avg, 2),
                'coverage': _round(coverage, 1) if coverage is not None else '', 'priority': priority,
                'suggested_units': suggested, 'suggested_text': text,
            }
            b = last_buy.get(product.pk)
            item['last_provider'] = b['buy_id__provider__names'] if b else ''
            item['last_date'] = b['buy_id__date_joined'].strftime('%Y-%m-%d') if b else ''
            if can_costs:
                item['est_cost'] = _round(suggested * h['cost'])
                item['last_cost'] = _round(_f(b['price'])) if b else ''
                item['last_cost_label'] = b['presentation_name'] or (product.unit_name or 'Unidad') if b else ''
            rows.append(item)
    order = {'Crítico': 0, 'Urgente': 1, 'Pronto': 2, 'Cubierto': 3}
    rows.sort(key=lambda i: (order[i['priority']], i['coverage'] if i['coverage'] != '' else 1e9, i['name']))

    kpis = [
        {'label': 'Referencias a reponer', 'value': sum(1 for i in rows if i['suggested_units'] > 0), 'type': 'number'},
        {'label': 'Críticas (agotadas)', 'value': sum(1 for i in rows if i['priority'] == 'Crítico'), 'type': 'number'},
        {'label': 'Urgentes (< 3 días)', 'value': sum(1 for i in rows if i['priority'] == 'Urgente'), 'type': 'number'},
    ]
    if can_costs:
        kpis.append({'label': 'Inversión estimada', 'value': _round(sum(i['est_cost'] for i in rows)), 'type': 'money'})
    notes = [f'Promedio diario calculado con las ventas de los últimos {days} días; la sugerencia busca cubrir {cover} días '
             '(o llegar al stock mínimo si lo definió). La cantidad sugerida se expresa en la presentación más grande que alcance.']
    return {'kpis': kpis, 'rows': rows, 'chart': None, 'summary': None, 'notes': notes}


# --------------------------------------------------------------------------- rotación e inactivos
def rotation(params, can_costs):
    days = _int(params.get('days'), 90)
    dormant = _int(params.get('dormant'), 60)
    today = date.today()
    since = today - timedelta(days=days - 1)

    sold = defaultdict(lambda: {'revenue': 0.0, 'units': 0.0})
    for d in _sale_lines(since, today, category=params.get('category')).values('product_id', 'total', 'cant', 'factor'):
        s = sold[d['product_id']]
        s['revenue'] += _f(d['total'])
        s['units'] += d['cant'] * _f(d['factor'])
    last_sale = dict(SaleDetail.objects.filter(is_active=True, sale__is_active=True)
                     .values_list('product_id').annotate(last=Max('sale__date_joined')))

    rows = []
    for product in _active_products(params):
        s = sold.get(product.pk, {'revenue': 0.0, 'units': 0.0})
        holders = holders_of(product)
        stock = sum(h['stock'] for h in holders)
        value_cost = sum(h['stock'] * h['cost'] for h in holders)
        last = last_sale.get(product.pk)
        days_since = (today - last).days if last else None
        daily = s['units'] / days
        days_inventory = stock / daily if daily > 0 else None
        if stock > 0 and (days_since is None or days_since > dormant):
            status = 'Sin movimiento'
        elif days_inventory is not None and days_inventory > 90:
            status = 'Lento'
        elif s['units'] > 0:
            status = 'Activo'
        else:
            status = 'Sin ventas en el período' if stock > 0 else 'Agotado sin ventas'
        item = {
            'code': product.code, 'name': product.name, 'category': product.category.name, 'abc': '',
            'revenue': _round(s['revenue']), 'share': 0, 'cumulative': 0, 'units': _round(s['units'], 2),
            'stock': _round(stock, 2),
            'rotation': _round(s['units'] / stock, 2) if stock > 0 and s['units'] else 0,
            'days_inventory': _round(days_inventory, 1) if days_inventory is not None else '',
            'last_sale': last.strftime('%Y-%m-%d') if last else 'Nunca', 'days_since': days_since if days_since is not None else '',
            'status': status,
        }
        if can_costs:
            item['stuck'] = _round(value_cost) if status in ('Sin movimiento', 'Sin ventas en el período') else 0
            item['value_cost'] = _round(value_cost)
        rows.append(item)

    total = sum(i['revenue'] for i in rows)
    rows.sort(key=lambda i: (-i['revenue'], i['name']))
    cum = 0.0
    for i in rows:
        if i['revenue'] > 0 and total:
            i['share'] = _round(i['revenue'] / total * 100, 1)
            cum += i['revenue']
            i['cumulative'] = _round(cum / total * 100, 1)
            i['abc'] = 'A' if i['cumulative'] - i['share'] < 80 else ('B' if i['cumulative'] - i['share'] < 95 else 'C')
        else:
            i['abc'] = '-'

    class_a = [i for i in rows if i['abc'] == 'A']
    idle = [i for i in rows if i['status'] == 'Sin movimiento']
    kpis = [
        {'label': 'Productos clase A (≈80% de las ventas)', 'value': len(class_a), 'type': 'number'},
        {'label': f'Sin movimiento (> {dormant} días)', 'value': len(idle), 'type': 'number'},
        {'label': 'Ventas del período', 'value': _round(total), 'type': 'money'},
    ]
    if can_costs:
        kpis.append({'label': 'Capital detenido (a costo)', 'value': _round(sum(i['stuck'] for i in rows)), 'type': 'money'})
    top = [i for i in rows if i['revenue'] > 0][:15]
    chart = {'title': 'Pareto de ventas (los productos que más aportan)', 'categories': [i['name'] for i in top], 'dual': True,
             'series': [{'name': 'Ventas', 'type': 'column', 'data': [i['revenue'] for i in top], 'money': True},
                        {'name': '% acumulado', 'type': 'line', 'yAxis': 1, 'data': [i['cumulative'] for i in top], 'suffix': '%'}]}
    notes = [f'Ventas de los últimos {days} días. Clase A: productos que juntos hacen cerca del 80% de las ventas; B hasta el 95%; '
             f'C el resto. "Sin movimiento": tienen stock y no se venden hace más de {dormant} días. "Lento": el stock alcanzaría más de 90 días.']
    return {'kpis': kpis, 'rows': rows, 'chart': chart, 'summary': None, 'notes': notes}
