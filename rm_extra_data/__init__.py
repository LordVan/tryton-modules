from trytond.pool import Pool
from . import party
from . import sale
from . import stock
from . import product

def register():
    Pool.register(
        party.Party,
        product.Product,
        product.Template,
        sale.Sale,
        sale.SaleContact,
        sale.SaleLine,
        stock.Move,
        stock.ShipmentOut,
        module='rm_extra_data', type_='model')
    Pool.register(
        sale.AmendmentLine,
        module='rm_extra_data', type_='model',
        depends=['sale_amendment'])

    Pool.register(
        sale.SaleReport,
        stock.DeliveryNote,
        module='rm_extra_data', type_='report')
    
    
    
    
