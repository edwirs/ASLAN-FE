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

TAX_RESPONSIBILITY = (
    ('no_responsable', 'No responsable de IVA'),
    ('responsable', 'Responsable de IVA'),
)