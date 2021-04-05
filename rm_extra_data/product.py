from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)

__all__ = ['Product']

class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    material = fields.Char('Material',
                           states = {'readonly': Eval('sale_state') != 'draft', },
                           help = 'Material name (auto-filled from product)')
    material_extra = fields.Char('Material extra text',
                                 states = { 'readonly': Eval('sale_state') != 'draft', },
                                 help = 'extra text to be appended to material')
    material_surface = fields.Char('Material surface',
                                   states = { 'readonly': Eval('sale_state') != 'draft', },
                                   help = 'surface treatment for material (paint,..) ')
    # this is actually also used for non sheet metal thickness, but not going to rename the field, just changing the description
    sheet_thickness = fields.Float('Material thickness',
                                   states = { 'readonly': Eval('sale_state') != 'draft', },
                                   digits = (2, 2),
                                   help = 'material thickness')
