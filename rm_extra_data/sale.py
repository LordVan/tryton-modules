from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)

__all__ = ['Sale', 'SaleLine']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    # extra fields:

    dolibarr_pid = fields.Integer('Dolibarr project id',
                                  #readonly = True,
                                  help = 'project id from dolibarr (for import purposes only)')
    sale_date_extra = fields.Char('Sale date extra',
                                  help = 'sale date extra text')
    sale_folder_postfix = fields.Char('Sale folder postfix',
                                      help = 'this will be appended to the folder name')
    shipping_date_extra = fields.Char('Shipping date extra',
                                      help ='shipping date extra text')


    # extra_contacts = fields.Many2Many('sale.sale-party.party',
    #                                   'party',
    #                                   'party',
    #                                   'Extra contacts')

    folder_total = fields.Integer('Total folder number',
                                  required = True,
                                  help = 'total number of folders (not counting subfolders)')
    

    @classmethod
    def default_folder_total(cls):    
        return 1
    
    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    @set_employee('confirmed_by')
    def confirm(cls, sales):
        # do not process automagically
        pass
    

class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    # extra fields
    folder_no = fields.Integer('Folder number',
                               required = True,
                               help = 'Folder number')
    folder_subcount = fields.Integer('Folder sub count',
                                     required = True,
                                     help = 'subfolder count')

    proj_line1 = fields.Char('Project sheet line 1',
                             required = True,
                             help = 'first line on the project sheets generated for this sale line')
    proj_line2 = fields.Char('Project sheet line 2',
                             help = 'second line on the project sheets generated for this sale line')
    # material
    material_extra = fields.Char('Material extra text',
                                 help = 'extra text to be appended to material')
    material_surface = fields.Char('Material surface',
                                   help = 'surface treatment for material (paint,..) ')
    sheet_thickness = fields.Float('Sheet metal thickness',
                                   digits = (2, 2),
                                   help = 'sheet metal thickness')

    @classmethod
    def default_folder_no(cls):
        # TODO: maybe use highet existing as default ?
        return 1

    @classmethod
    def default_folder_subcount(cls):
        return 1