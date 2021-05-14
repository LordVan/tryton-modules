from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)

__all__ = ['Product']

class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    real_product = fields.Boolean('Real product',
                                  help = 'if selected this is a real, final product, not a placeholder')
    folder_subno = fields.Char('Subfolder',
                               states = { 'readonly':  Eval('folder_skip', True), },
                               help = 'Subfolder number (letter)')
    folder_submax = fields.Char('Subfolder maximum',
                                states = { 'readonly': Eval('folder_skip', True), },
                                help = 'Subfolder maximum')
    folder_skip = fields.Boolean('Skip this on project sheets',
                                 help = 'if selected this sale line will not show on project sheets')
    # TODO: should I mahe the project lines readonly on the form too when skipped? ..
    proj_line0 = fields.Char('Project sheet line 0',
                             help = 'above first line on the project sheets generated for this sale line')
    proj_line1 = fields.Char('Project sheet line 1',
                             #required = True, # not required on product, but only on sale line !!
                             help = 'first line on the project sheets generated for this sale line')
    proj_line2 = fields.Char('Project sheet line 2',
                             help = 'second line on the project sheets generated for this sale line')
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

    # extra fields for delivery notes / invoices (where it does not match the normal lines)
    # line(s)

    inv_skip = fields.Boolean('Skip this whole sale line for invoice / delivery note',
                              help = 'if selected this sale line will not show on invoices or delivery notes')
    inv_line0 = fields.Char('Invoice / delivery note line 0',
                             states = {'readonly': (Eval('inv_line0_skip', True) | Eval('inv_skip', True)), },
                             help = 'above first line on the invoice / delivery note generated for this sale line.')
    inv_line0_skip = fields.Boolean('Skip invoice / delivery note line 0',
                                    states = {'readonly': Eval('inv_skip', True), },
                                    help = 'if selected invoice line 0 will be ignored')
    inv_line1 = fields.Char('Invoice / delivery note line 1',
                            states = { 'readonly': Eval('inv_skip', True), },
                             help = 'first line on the invoice / delivery note generated for this sale line')
    inv_line2 = fields.Char('Invoice / delivery note line 2',
                             states = {'readonly': (Eval('inv_line2_skip', True) | Eval('inv_skip', True)), },
                             help = 'second line on the invoice / delivery note generated for this sale line')
    inv_line2_skip = fields.Boolean('Skip invoice / delivery note line 2',
                                    states = {'readonly': Eval('inv_skip', True), },
                                    help = 'if selected invoice line 2 will be ignored')

    @classmethod
    def default_real_product(cls):
        return True
