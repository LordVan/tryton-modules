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
                           help = 'Material name (auto-filled from product)')
    material_extra = fields.Char('Material extra text',
                                 help = 'extra text to be appended to material (usually only needed on sale line)')
    material_surface = fields.Char('Material surface',
                                   help = 'surface treatment for material (paint,..) (usually only needed on sale line)')
    # this is actually also used for non sheet metal thickness, but not going to rename the field, just changing the description
    sheet_thickness = fields.Float('Material thickness',
                                   digits = (2, 2),
                                   help = 'material thickness')
