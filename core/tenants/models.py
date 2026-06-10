from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Client(TenantMixin):
    name = models.CharField(max_length=150, verbose_name='Razón social')
    nit = models.CharField(max_length=20,unique=True,verbose_name='NIT')
    email = models.EmailField(blank=True,null=True)
    phone = models.CharField(max_length=20,blank=True,null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    paid_until = models.DateField(null=True,blank=True)
    on_trial = models.BooleanField(default=True)
    auto_create_schema = True

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass