from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)
from trytond.exceptions import UserWarning, UserError

__all__ = ['Sale', 'SaleLine', 'SaleContact', 'SaleReport']


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
    due_date = fields.Date('Due date',
                           states = { 'readonly': Eval('state') != 'draft', },
                           help = 'Due date for this sale')
    # TODO: renomae to due_date_extra 
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
    @Workflow.transition('quotation')
    @set_employee('quoted_by')
    def quote(cls, sales):
        super(Sale, cls).quote(sales)
        # we need to apply folder_no to components of kits
        for sale in sales:
            for line in sale.lines:
                for lc in line.component_children:
                    lc.folder_no = line.folder_no
                    lc.save()
        cls.save(sales)
    
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
            if not sale.party.pn_name or len(sale.party.pn_name.strip()) < 1:
                raise UserError('Verkaufsparteien müssen einen PN Namen zugewiesen haben.')
            for line in sale.lines:
                if not line.product:
                    need_fixing.append(line.rec_name)
        if Warning.check(warning_name):
            if need_fixing:
                msg = 'Position ohne Produkt gefunden!!'
                #msg += '\n'.join(need_fixing)
                raise UserWarning(warning_name, msg)
        warning_sale_date_extra = 'sale_date_extra,%s' % cls
        warn_sale_date = []
        for sale in sales:
            others = Pool().get('sale.sale').search([('sale_folder_postfix', '=', sale.sale_folder_postfix),
                                                     ('party', '=', sale.party),
                                                     ('sale_date', '=', sale.sale_date),
                                                     ('number', '!=', sale.number), ])
            for s in others:
                warn_sale_date.append(s.number)
        if Warning.check(warning_sale_date_extra):
            if warn_sale_date:
                msg = 'Verkauf für diesen Kunden mit gleichem Bestelldatum und Bestellordner Zusatz existiert bereits:'
                msg += '\n'.join(warn_sale_date)
                raise UserWarning(warning_sale_date_extra, msg)


class SaleReport(metaclass=PoolMeta):
    __name__ = 'sale.sale.project'

    @classmethod
    def get_context(cls, records, header, data):
        context = super(SaleReport, cls).get_context(records, header, data)
        def get_project_lines(sale):
            sorted_lines = list(filter(lambda x: x.folder_skip == False, sale.lines)) # copy the list but filter skipped ones here
            if not sorted_lines:
                # we got nothing
                # TODO: raise an error, or just let the user figure it out?␘
                return []
            # for project sheets we sort lines by folder number, then subfolder number
            # also makes it a lot easier to combine lines for project sheets
            sorted_lines.sort(key=lambda x: (x.folder_no, x.folder_subno))
            merged_lines = []
            # the next line to be added (after potential merging)
            next_line = sorted_lines[0]
            try:
                next_line0_text = next_line.proj_line0.strip()
            except:
                next_line0_text = ''
            next_line1 = [next_line,]
            try:
                next_line2_text = next_line.proj_line2.strip()
            except:
                next_line2_text = ''
            for line in sorted_lines[1:]:
                if (line.folder_no == next_line.folder_no and
                    line.folder_subno == next_line.folder_subno and
                    line.material == next_line.material and
                    line.material_extra == next_line.material_extra and
                    line.material_surface == next_line.material_surface and
                    line.sheet_thickness == next_line.sheet_thickness and
                    line.due_date == next_line.due_date and
                    line.due_date_postfix == next_line.due_date_postfix):
                    # this line matches the next line to be added so append data
                    try:
                        if line.proj_line0.strip():
                            next_line0_text += line.proj_line0.strip()
                    except:
                        pass # ignore NoneType error
                    next_line1.append(line)
                    try:
                        if line.proj_line2.strip():
                            next_line2_text += line.proj_line2.strip()
                    except:
                        pass # ignore NoneType error
                    # do not merge anything else at this point
                else:
                    # we need a new sheet ..
                    merged_lines.append((next_line, next_line0_text, next_line1, next_line2_text)) # append the last line
                    next_line = line # the current line is now the next one
                    # assign initial values
                    try:
                        next_line0_text = next_line.proj_line0.strip()
                    except:
                        next_line0_text = ''
                    next_line1 = [next_line,]
                    try:
                        next_line2_text = next_line.proj_line2.strip()
                    except:
                        next_line2_text = ''
            # Important: append the last line
            merged_lines.append((next_line, next_line0_text, next_line1, next_line2_text)) # append the last line
            return merged_lines
        context['get_project_lines'] = get_project_lines
        return context
            
class SaleContact(ModelSQL):
    "Sale - Contact"
    __name__ = 'party.party-sale.sale'
    sale = fields.Many2One('sale.sale', "Sale", ondelete='CASCADE', select=True, required=True)
    party = fields.Many2One('party.party', "Contact", ondelete='CASCADE', required=True)
                    
            

class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    # extra fields
    real_product = fields.Boolean('Real product',
                                  states = { 'invisible': True, },
                                  help = 'this gets set if data is filled in from an actual product')
    folder_no = fields.Integer('Folder number',
                               required = True,
                               states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                       Eval('folder_skip')),
                               },
                               help = 'Folder number')
    folder_subno = fields.Char('Subfolder',
                               states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                       Eval('folder_skip') |
                                                       Eval('real_product')),
                               },
                               help = 'Subfolder number (letter)')
    folder_submax = fields.Char('Subfolder maximum',
                                states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                        Eval('folder_skip') |
                                                        Eval('real_product')),
                                },
                                help = 'Subfolder maximum')
    folder_skip = fields.Boolean('Skip this on project sheets',
                                 states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                        Eval('real_product')),
                                 },
                                 help = 'if selected this sale line will not show on project sheets')
    due_date = fields.Date('Due date',
                           states = { 'readonly': Eval('sale_state') != 'draft', },
                           help = 'Due date for this sale line (replaces due date from project sheet)')

    due_date_postfix = fields.Char('Due date extra',
                                   states = { 'readonly': Eval('sale_state') != 'draft', },
                                   help = 'Extra text for due date for this sale line (replaces due date extra from project sheet ')
    proj_line0 = fields.Char('Project sheet line 0',
                             states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                     Eval('real_product')),
                             },
                             help = 'above first line on the project sheets generated for this sale line')
    proj_line1 = fields.Char('Project sheet line 1',
                             required = True,
                             states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                     Eval('real_product')),
                             },
                             help = 'first line on the project sheets generated for this sale line')
    proj_line2 = fields.Char('Project sheet line 2',
                             states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                     Eval('real_product')),
                             },
                             help = 'second line on the project sheets generated for this sale line')
    proj_impnote = fields.Char('Project important notes',
                               states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                      Eval('real_product')),
                               },
                               help = 'important production notes')
    material = fields.Char('Material',
                           states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                  Eval('product') |
                                                  Eval('real_product')),
                           },
                           help = 'Material name (auto-filled from product)')
    # those 2 are not usually set on the product (at least not for now so leave them read-write
    # TODO: maybe make them readonly only if values were set from the product
    material_extra = fields.Char('Material extra text',
                                 states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                         Eval('real_product')),
                                 },
                                 #states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                                 help = 'extra text to be appended to material')
    material_surface = fields.Char('Material surface',
                                   states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                           Eval('real_product')),
                                   },
                                   #states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                                   help = 'surface treatment for material (paint,..) ')
    # this is actually also used for non sheet metal thickness, but not going to rename the field, just changing the description
    sheet_thickness = fields.Float('Material thickness',
                                   states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                          Eval('product') |
                                                          Eval('real_product')),
                                   },
                                   digits = (2, 2),
                                   help = 'material thickness')
    
    # extra fields for delivery notes / invoices (where it does not match the normal lines)
    # line(s)

    inv_skip = fields.Boolean('Skip this whole sale line for invoice / delivery note',
                              states = { 'readonly': ((Eval('sale_state') != 'draft') |
                                                      Eval('real_product')),
                              },
                              help = 'if selected this sale line will not show on invoices or delivery notes')
    
    inv_line0 = fields.Char('Invoice / delivery note line 0',
                             states = {
                                 'readonly': ((Eval('sale_state') != 'draft') |
                                              Eval('inv_line0_skip') |
                                              Eval('inv_skip') |
                                              Eval('real_product')
                                 ),
                             },
                             help = 'above first line on the invoice / delivery note generated for this sale line.')
    inv_line0_skip = fields.Boolean('Skip invoice / delivery note line 0',
                                    states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                           Eval('inv_skip') |
                                                           Eval('real_product')),
                                    },
                                    help = 'if selected invoice line 0 will be ignored')
    inv_line1 = fields.Char('Invoice / delivery note line 1',
                             states = {
                                 'readonly': ((Eval('sale_state') != 'draft') |
                                              Eval('inv_skip') |
                                              Eval('real_product')),
                             },
                             help = 'first line on the invoice / delivery note generated for this sale line')
    inv_line2 = fields.Char('Invoice / delivery note line 2',
                             states = {
                                 'readonly': ((Eval('sale_state') != 'draft') |
                                              Eval('inv_line2_skip') |
                                              Eval('inv_skip') |
                                              Eval('real_product')),
                             },
                             help = 'second line on the invoice / delivery note generated for this sale line')
    inv_line2_skip = fields.Boolean('Skip invoice / delivery note line 2',
                                    states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                           Eval('inv_skip') |
                                                           Eval('real_product')),
                                    },
                                    help = 'if selected invoice line 2 will be ignored')

    @classmethod
    def default_real_product(cls):
        return False
    
    @classmethod
    def default_folder_skip(cls):
        return False
    
    @classmethod
    def default_folder_no(cls):
        # TODO: maybe use highest existing as default ?
        return 1

    @fields.depends('material', 'material_extra', 'sheet_thickness', 'material_surface', 'real_product', 'folder_skip')
    def on_change_product(self):
        # TODO: set material and sheet_thickness as readonly normally and only allow overwriting if no product is set?
        super(SaleLine, self).on_change_product()
        if not self.product:
            #reset real_product to false as the product was removed
            self.real_product = False
            return
        
        # fields that are always set as soon as a product is chosen:
        self.real_product = self.product.real_product
        # overwriting material and material thickness
        self.material = self.product.material
        self.sheet_thickness = self.product.sheet_thickness
        
        if not self.product.real_product:
            # this is a placeholder product not a real one so only copy basic data
            # those two won't usually be set so do not overwrite with empty values
            if self.product.material_extra:
                self.material_extra = self.product.material_extra
            if self.product.material_surface:
                self.material_surface = self.product.material_surface
        else:
            # copy all data from the product since this is an actual product and nto a placeholder
            # overwriting everything here even if empty
            self.folder_subno = self.product.folder_subno
            self.folder_submax = self.product.folder_submax
            self.folder_skip = self.product.folder_skip
            self.proj_line0 = self.product.proj_line0
            if not self.product.proj_line1:
                raise UserError('Produkte ohne Projektzeile 1 können nicht hinzugefügt werden.')
            self.proj_line1 = self.product.proj_line1
            self.proj_line2 = self.product.proj_line2
            self.proj_impnote = self.product.proj_impnote
            self.material_extra = self.product.material_extra
            self.material_surface = self.product.material_surface
            # material and sheet_thickness are set above in any case
            self.inv_skip = self.product.inv_skip
            self.inv_line0 = self.product.inv_line0
            self.inv_line0_skip = self.product.inv_line0_skip
            self.inv_line1 = self.product.inv_line1
            self.inv_line2 = self.product.inv_line2
            self.inv_line2_skip = self.product.inv_line2_skip

