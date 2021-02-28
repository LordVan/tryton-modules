from trytond.pool import Pool
from . import party
from . import sale

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
    
    
