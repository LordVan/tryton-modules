from trytond.pool import Pool
from . import party
from . import sale
from . import product

def register():
    Pool.register(
        party.Party,
        module='rm_extra_data', type_='model')
    Pool.register(
        sale.Sale,
        module='rm_extra_data', type_='model')
    Pool.register(
        sale.SaleLine,
        module='rm_extra_data', type_='model')
    Pool.register(
        product.Product,
        module='rm_extra_data', type_='model')
    Pool.register(
        sale.SaleContact,
        module='rm_extra_data', type_='model')
    
    
    
    
