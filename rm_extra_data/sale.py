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
                                  states = {
                                      'readonly': Eval('state') != 'draft',
                                      'invisible': True,
                                  },
                                  help = 'project id from dolibarr (for import purposes only)')
    sale_date_extra = fields.Char('Sale date extra',
                                  states = { 'readonly': Eval('state') != 'draft', },
                                  help = 'sale date extra text')
    sale_folder_postfix = fields.Char('Sale folder postfix',
                                      states = { 'readonly': Eval('state') != 'draft', },
                                      help = 'this will be appended to the folder name')
    shipping_date_extra = fields.Char('Shipping date extra',
                                      states = { 'readonly': Eval('state') != 'draft', },
                                      help ='shipping date extra text')


    # extra_contacts = fields.Many2Many('sale.sale-party.party',
    #                                   'party',
    #                                   'party',
    #                                   'Extra contacts')

    folder_total = fields.Integer('Total folder number',
                                  required = True,
                                  states = { 'readonly': Eval('state') != 'draft', },
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
                               states = { 'readonly': Eval('sale_state') != 'draft', },
                               help = 'Folder number')
#    folder_subcount = fields.Integer('Folder sub count',
#                                     required = True,
#                                     help = 'subfolder count')

    folder_subno = fields.Char('Subfolder',
                               states = { 'readonly': Eval('sale_state') != 'draft', },
                               help = 'Subfolder number (letter)')
    folder_submax = fields.Char('Subfolder maximum',
                                states = { 'readonly': Eval('sale_state') != 'draft', },
                                help = 'Subfolder maximum')

    due_date = fields.Date('Due date',
                           states = { 'readonly': Eval('sale_state') != 'draft', },
                           help = 'Due date for this sale line (replaces due date from project sheet)')

    due_date_postfix = fields.Char('Due date extra',
                                   states = { 'readonly': Eval('sale_state') != 'draft', },
                                   help = 'Extra text for due date for this sale line (replaces due date extra from project sheet ')
    
    proj_line0 = fields.Char('Project sheet line 0',
                             states = { 'readonly': Eval('sale_state') != 'draft', },
                             help = 'above first line on the project sheets generated for this sale line')
    
    proj_line1 = fields.Char('Project sheet line 1',
                             required = True,
                             states = { 'readonly': Eval('sale_state') != 'draft', },
                             help = 'first line on the project sheets generated for this sale line')
    proj_line2 = fields.Char('Project sheet line 2',
                             states = { 'readonly': Eval('sale_state') != 'draft', },
                             help = 'second line on the project sheets generated for this sale line')
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

    @classmethod
    def default_folder_no(cls):
        # TODO: maybe use highet existing as default ?
        return 1

    @classmethod
    def default_folder_subcount(cls):
        return 1
