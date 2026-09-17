GENDER = (
    ('male','Masculino'),
    ('female','Femenino'),
)

PAYMENTMETHODS = (
    ('cash', 'Efectivo'),
    ('creditCard', 'Tarjeta Crédito'),
    ('debitCard', 'Tarjeta Débito'),
    ('transfer', 'Transferencia'),
    ('mixto', 'Mixto'),
)

TYPETMETHODS = (
    ('fullpayment', 'Contado'),
    ('credit', 'Crédito'),
)

TRANSFERMETHODS = (
    ('nequi', 'Nequi'),
    ('daviplata', 'Daviplata'),
    ('mixto1', 'Nequi + Efectivo'),
    ('mixto2', 'Daviplata + Efectivo'),
    ('mixto3', 'Nequi + daviplata'),
)

EXPENSES = (
    ('caja', 'Caja'),
    ('general', 'General'),
    ('inventory', 'Inventario'),
)

SERVICE_TYPE = (
    ('in_site', 'En Sitio'),
    ('delivery', 'Domicilio'),
)

TIPO_CONTRATO = [
        ('F', 'Término Fijo'),
        ('I', 'Término Indefinido'),
        ('O', 'Obra o labor'),
        ('P', 'Prestación de servicios'),
    ]

PERIODO_NOMINA = [
        ('Q1', 'Primera quincena'),
        ('Q2', 'Segunda quincena'),
        ('M', 'Mensual'),
    ]

STATUS_CHOICES = (
        ('open', 'Abierto'),
        ('sent', 'En preparación'),
        ('ready', 'Listo'),
        ('closed', 'Cerrado'),
        ('cancelled', 'Cancelado'),
    )

EMPLOYEE_TRANSACTION_CHOICES = (
        ('loan', 'Préstamo'),
        ('advance', 'Adelanto'),
        ('product', 'Producto'),
        ('other', 'Otro'),
    )

AUTORIZATION_DISCOUNT = (
    ('cristian', 'Cristian Barragan'),
    ('randol', 'Randol Barragan'),
    ('diego', 'Diego Barragan'),
    ('steven', 'Steven Monroy'),
)

PERSON_TYPE = (
    ('natural', 'Persona Natural'),
    ('juridica', 'Persona Jurídica'),
)

# Códigos oficiales DIAN / Factus para notas crédito (tabla "Códigos de tipos
# de operación (notas crédito)" y "Códigos de corrección (notas crédito)").
# Ver: https://developers.factus.com.co/tablas-de-referencia/tablas/
CREDIT_NOTE_OPERATION_TYPE = (
    ('20', 'Nota crédito que referencia una factura electrónica'),
    ('22', 'Nota crédito sin referencia a una factura electrónica'),
)

CREDIT_NOTE_CORRECTION_CONCEPT = (
    ('1', 'Devolución parcial de los bienes y/o no aceptación parcial del servicio'),
    ('2', 'Anulación de factura electrónica'),
    ('3', 'Rebaja o descuento parcial o total'),
    ('4', 'Ajuste de precio'),
    ('5', 'Descuento comercial por pronto pago'),
    ('6', 'Descuento comercial por volumen de ventas'),
)

TAX_RESPONSIBILITY = (
    ('no_responsable', 'No responsable de IVA'),
    ('responsable', 'Responsable de IVA'),
)

FACTUS_ENVIRONMENT = (
    ('sandbox', 'Sandbox (pruebas)'),
    ('production', 'Producción'),
)