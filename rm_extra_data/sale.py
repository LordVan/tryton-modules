from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)
from trytond.exceptions import UserWarning

__all__ = ['Sale', 'SaleLine', 'SaleContact']


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


    extra_contacts = fields.Many2Many('party.party-sale.sale', 'sale', 'party', 'Extra Contacts',
                                      states = { 'readonly': Eval('state') != 'draft', })

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
        # skip original logic, so we do not process automagically
        Warning = Pool().get('res.user.warning')
        warning_name = 'saleline_noproduct,%s' % cls
        need_fixing = []
        for sale in sales:
            for line in sale.lines:
                if not line.product:
                    need_fixing.append(line.rec_name)
        if Warning.check(warning_name):
            if need_fixing:
                msg = 'Position ohne Produkt gefunden!!'
                #msg += '\n'.join(need_fixing)
                raise UserWarning(warning_name, msg)


class SaleContact(ModelSQL):
    "Sale - Contact"
    __name__ = 'party.party-sale.sale'
    sale = fields.Many2One('sale.sale', "Sale", ondelete='CASCADE', select=True, required=True)
    party = fields.Many2One('party.party', "Contact", ondelete='CASCADE', required=True)
                    
            

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
                           states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                           help = 'Material name (auto-filled from product)')
    # those 2 are not usually set on the product (at least not for now so leave them read-write
    # TODO: maybe make them readonly only if values were set from the product
    material_extra = fields.Char('Material extra text',
                                 states = { 'readonly': Eval('sale_state') != 'draft', },
                                 #states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                                 help = 'extra text to be appended to material')
    material_surface = fields.Char('Material surface',
                                   states = { 'readonly': Eval('sale_state') != 'draft', },
                                   #states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                                   help = 'surface treatment for material (paint,..) ')
    # this is actually also used for non sheet metal thickness, but not going to rename the field, just changing the description
    sheet_thickness = fields.Float('Material thickness',
                                   states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                                   digits = (2, 2),
                                   help = 'material thickness')
    
    # extra fields for delivery notes / invoices (where it does not match the normal lines)
    # line(s)

    inv_skip = fields.Boolean('Skip this whole sale line for invoice / delivery note',
                              help = 'if selected this sale line will not show on invoices or delivery notes')
    
    inv_line0 = fields.Char('Invoice / delivery note line 0',
                             states = {
                                 'readonly': ((Eval('sale_state') != 'draft')
                                              | Eval('inv_line0_skip')
                                              | Eval('inv_skip')
                                 ),
                             },
                             help = 'above first line on the invoice / delivery note generated for this sale line.')
    inv_line0_skip = fields.Boolean('Skip invoice / delivery note line 0',
                                    states = {'readonly': ((Eval('sale_state') != 'draft')
                                                           | Eval('inv_skip')),
                                    },
                                    help = 'if selected invoice line 0 will be ignored')
    inv_line1 = fields.Char('Invoice / delivery note line 1',
                             states = {
                                 'readonly': ((Eval('sale_state') != 'draft')
                                              | Eval('inv_skip')),
                             },
                             help = 'first line on the invoice / delivery note generated for this sale line')
    inv_line2 = fields.Char('Invoice / delivery note line 2',
                             states = {
                                 'readonly': ((Eval('sale_state') != 'draft')
                                              | Eval('inv_line2_skip')
                                              | Eval('inv_skip')),
                             },
                             help = 'second line on the invoice / delivery note generated for this sale line')
    inv_line2_skip = fields.Boolean('Skip invoice / delivery note line 2',
                                    states = {'readonly': ((Eval('sale_state') != 'draft')
                                                           | Eval('inv_skip')),
                                              },
                                    help = 'if selected invoice line 2 will be ignored')
 
    @classmethod
    def default_folder_no(cls):
        # TODO: maybe use highet existing as default ?
        return 1

    @classmethod
    def default_folder_subcount(cls):
        return 1

    @fields.depends('material', 'material_extra', 'sheet_thickness', 'material_surface')
    def on_change_product(self):
        # TODO: set material and sheet_thickness as readonly normally and only allow overwriting if no product is set?
        if not self.product:
            return

        super(SaleLine, self).on_change_product()

        # TODO: evaluate if we want to also overwrite with empty values or not
        self.material = self.product.material
        self.sheet_thickness = self.product.sheet_thickness
        # those two won't usually be set so do not overwrite with empty values FIXME: good or not?
        if self.product.material_extra:
            self.material_extra = self.product.material_extra
        if self.product.material_surface:
            self.material_surface = self.product.material_surface
            
