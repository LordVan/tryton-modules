from trytond.pool import Pool
from . import party
from . import sale
from . import stock
from . import product
from . import invoice
from . import routes

__all__ = ['register', 'routes']

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
        invoice.Invoice,
        invoice.InvoiceLine,
        module='rm_extra_data', type_='model')
    Pool.register(
        sale.AmendmentLine,
        module='rm_extra_data', type_='model',
        depends=['sale_amendment'])

    Pool.register(
        sale.SaleReport,
        stock.DeliveryNote,
        invoice.InvoiceReport,
        module='rm_extra_data', type_='report')
    
    Pool.register(
        party.Replace,
        module='rm_extra_data', type_='wizard')
    
    
    
