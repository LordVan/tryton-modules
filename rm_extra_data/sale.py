from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)
from trytond.exceptions import UserWarning, UserError

import logging
logger = logging.getLogger(__name__)

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
                                  states = { 'readonly': ~Eval('state').in_(['draft', 'quotation']), },
                                  help = 'sale date extra text')
    sale_folder_postfix = fields.Char('Sale folder postfix',
                                      states = { 'readonly': Eval('state').in_(['done', 'cancelled']), },
                                      help = 'this will be appended to the folder name')
    due_date = fields.Date('Due date',
                           states = { 'readonly': ~Eval('state').in_(['draft', 'quotation']), },
                           help = 'Due date for this sale')
    # TODO: rename to due_date_extra 
    shipping_date_extra = fields.Char('Shipping date extra',
                                      states = { 'readonly': ~Eval('state').in_(['draft', 'quotation']), },
                                      help ='shipping date extra text')


    extra_contacts = fields.Many2Many('party.party-sale.sale', 'sale', 'party', 'Extra Contacts',
                                      states = { 'readonly': ~Eval('state').in_(['draft', 'quotation']), })

    folder_total = fields.Integer('Total folder number',
                                  required = True,
                                  states = { 'readonly': Eval('state') != 'draft', },
                                  help = 'total number of folders (not counting subfolders)')
    offer_number = fields.Char('Offer number',
                               states = { 'readonly': ~Eval('state').in_(['draft', 'quotation']), },
                               help = 'Offer number')
    offer_date = fields.Date('Offer date',
                             states = { 'readonly': ~Eval('state').in_(['draft', 'quotation']), },
                             help = 'Offer date')
    sale_group_name = fields.Char('Sale group name',
                                  help = 'Name for the sale/invoice group used by custom invoice grouping')
    sale_note = fields.Char('Sale notes',
                            help = 'Notes for sale (will copied from party upon selection of customer)'
                            )

    @classmethod
    def __setup__(cls):
        super().__setup__()
        if 'readonly' in cls.description.states.keys():
            cls.description.states.update({
                'readonly': Eval('state').in_(['done', 'cancelled'])
                })

    # def _get_invoice_grouping_fields(self, invoice):
    #     return super()._get_invoice_grouping_fields(invoice) + ['sale_group_name']

    def create_invoice(self):
        inv = super().create_invoice()
        if inv:
            inv.sale_group_name = self.sale_group_name
        return inv
    
    @classmethod
    def default_folder_total(cls):    
        return 1

    @fields.depends(
        'company', 'party', 'invoice_party', 'shipment_party', 'warehouse',
        'payment_term', 'lines', methods=['update_sale_note'])
    def on_change_party(self):
        super().on_change_party()
        self.update_sale_note()

    @fields.depends('party', 'invoice_party', methods=['update_sale_note'])
    def on_change_invoice_party(self):
        super().on_change_invoice_party()
        self.update_sale_note()

    @fields.depends('party', 'shipment_party', 'warehouse', methods=['update_sale_note'])
    def on_change_shipment_party(self):
        super().on_change_shipment_party()
        self.update_sale_note()

    @fields.depends('party', 'shipment_party', 'invoice_party', 'sale_note')
    def update_sale_note(self):
        '''
        Update sale_note from all involved parties
        (needs to be called from all on_change*party methods as we combine all sale notes into one string)
        '''
        sale_note_text = ''
        if self.party:
            if self.party.sale_note and self.party.sale_note.strip():
                if self.invoice_party or self.shipment_party:
                    # we got more than one parties involved so add prefix
                    sale_note_text = 'B: '
                sale_note_text += self.party.sale_note.strip()
            if self.shipment_party and self.shipment_party.sale_note and self.shipment_party.sale_note.strip():
                if sale_note_text:
                    sale_note_text += ' /'
                sale_note_text += ' L: ' + self.shipment_party.sale_note.strip()
            if self.invoice_party and self.invoice_party.sale_note and self.invoice_party.sale_note.strip():
                if sale_note_text:
                    sale_note_text += ' /'
                sale_note_text += ' R: ' + self.invoice_party.sale_note.strip()
        self.sale_note = sale_note_text # we do always overwrite even if empty

    @classmethod
    @ModelView.button
    @Workflow.transition('quotation')
    @set_employee('quoted_by')
    def quote(cls, sales):
        # do the extra checks *before* calling super() !
        for sale in sales:
            # we definitely need to have a party at this point already as one cannot proceed without
            if not sale.party.pn_name or not sale.party.pn_name.strip():
                raise UserError('Partei Feld PN Name darf nicht leer sein.')
            if not sale.party.inv_name_line1 or not sale.party.inv_name_line1.strip():
                raise UserError('Partei Feld "Name Zeile 1 Rechnung/Lieferschein darf nicht leer sein.')
            if not sale.party.inv_name_line2 or not sale.party.inv_name_line2.strip():
                raise UserError('Partei Feld "Name Zeile 2 Rechnung/Lieferschein darf nicht leer sein.')
            if sale.invoice_party:
                if not sale.invoice_party.inv_name_line1 or not sale.invoice_party.inv_name_line1.strip():
                    raise UserError('Rechnungspartei Feld "Name Zeile 1 Rechnung/Lieferschein darf nicht leer sein.')
                if not sale.invoice_party.inv_name_line2 or not sale.invoice_party.inv_name_line2.strip():
                    raise UserError('Rechnungspartei Feld "Name Zeile 2 Rechnung/Lieferschein darf nicht leer sein.')
            if sale.shipment_party:
                if not sale.shipment_party.inv_name_line1 or not sale.shipment_party.inv_name_line1.strip():
                    raise UserError('Lieferpartei Feld "Name Zeile 1 Rechnung/Lieferschein darf nicht leer sein.')
                if not sale.shipment_party.inv_name_line2 or not sale.shipment_party.inv_name_line2.strip():
                    raise UserError('Lieferpartei Feld "Name Zeile 2 Rechnung/Lieferschein darf nicht leer sein.')
            if not sale.payment_term:
                raise UserError('Das Feld Zahlungsbedingungen darf nicht leer sein.')
        super(Sale, cls).quote(sales)
        # we need to apply folder_no to components of kits and do some checks
        # doing this after the call to super() as there should be no problems anymore here that could
        # cause number sequence skips
        for sale in sales:
            # Make sure folder numbers are on the component project sheets
            for line in sale.lines:
                for lc in line.component_children:
                    lc.folder_no = line.folder_no
                    lc.due_date = line.due_date
                    lc.due_date_postfix = line.due_date_postfix
                    lc.save()
        cls.save(sales)
    
    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    @set_employee('confirmed_by')
    def confirm(cls, sales):
        Warning = Pool().get('res.user.warning')
        # make sure noone is able to confirm a sale with shipment or invoice methods we do not want
        for sale in sales:
            if sale.shipment_method != 'order':
                raise UserError('Liefermethode ungültig')
            if sale.invoice_method != 'shipment':
                raise UserError('Rechnungmethode ungültig')
            if not sale.payment_term:
                raise UserError('Keine Zahlungsbedingungen angegeben!')
        # first check if we have a line without product and issue a warning
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
        # check if we already have an order fromt his customer for this date with the same sale_date_extra
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
        # give the users a warning before actually confirming an order and creating shipments,..
        confirm_warning = 'sale_confirm,%s' % cls
        if Warning.check(confirm_warning):
            raise UserWarning(confirm_warning, 'Bestätigen des Verkaufs erzeugt einen Lieferschein - fortfahren?')
        super(Sale, cls).confirm(sales)

    def _get_shipment_sale(self, Shipment, key):
        # Add sale reference / description[commission] to shipment
        # FIXME: would cause problems with shipment grouping !!
        shipment = super()._get_shipment_sale(Shipment, key)
        # add commission / customer reference as shipment reference by default
        ref = ''
        if self.reference and self.reference.strip():
            ref += self.reference.strip()
        if self.description and self.description.strip():
            if ref:
                ref += ' / '
            ref += self.description.strip()
        shipment.sale_refs = ref
        return shipment

class SaleReport(metaclass=PoolMeta):
    __name__ = 'sale.sale.project'

    @classmethod
    def get_context(cls, records, header, data):
        context = super(SaleReport, cls).get_context(records, header, data)
        for rec in records:
            if not rec.sale_date:
                raise UserError(f'Bestelldatum fehlt (Verkauf {rec.number})')
            if not rec.number:
                raise UserError('Projektzettel kann nicht ohne Verkaufsnummer (Projektnummer) erstellt werden.')
            if not rec.party and (not rec.party.pn_name and not self.party.pn_name.strip()):
                raise UserError('Partei muss PN Namen vergeben haben für Verkauf!')
            
        def get_project_sheets(sale):
            # Helper to get project lines, sort them and merge if needed
            # Returns a list of lists in the following format:
            # (line, merged line 0 text, lines (all lines), merged line 2 text, merged important notes)
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
            next_sheet= sorted_lines[0]
            try:
                next_line0_text = next_sheet.proj_line0.strip()
            except:
                next_line0_text = ''
            next_lines = [next_sheet,]
            try:
                next_line2_text = next_sheet.proj_line2.strip()
            except:
                next_line2_text = ''
                
            def merge_lines(lines):
                # helper to merge line texts
                # returns following format (list):
                # (merged line0 text, merged line2 text, merged important notes, merged cad/nc notes , ... )
                line0_text = ''
                line2_text = ''
                impnotes = []
                impnotes_text = ''
                notes_cadnc = []
                note_cadnc_text = ''
                notes_laser = []
                note_laser_text = ''
                notes_bend = []
                note_bend_text = ''
                notes_misc = []
                note_misc_text = ''
                notes_surface = []
                note_surface_text = ''
                for line in lines:
                    #logger.info(f'merge_lines: {line.proj_line1}')
                    # first sort out line0 and line2 merged texts
                    try:
                        if line.proj_line0 and line.proj_line0.strip():
                            if line0_text:
                                line0_text += ' ' # add a whitespace
                            line0_text += line.proj_line0.strip()
                    except:
                        raise UserError('Error merging line0')
                    try:
                        if line.proj_line2 and line.proj_line2.strip():
                            if line2_text:
                                line2_text += ' ' # add whitespace
                            line2_text += line.proj_line2.strip()
                    except:
                        raise UserError('Error merging line2')
                    # now find the various note fields that may need merging
                    try:
                        if line.proj_impnote.strip():
                            impnotes.append(line)
                    except:
                        pass
                    try:
                        if line.proj_note_cadnc.strip():
                            notes_cadnc.append(line)
                    except:
                        pass
                    try:
                        if line.proj_note_laser.strip():
                            notes_laser.append(line)
                    except:
                        pass
                    try:
                        if line.proj_note_bend.strip():
                            notes_bend.append(line)
                    except:
                        pass
                    try:
                        if line.proj_note_misc.strip():
                            notes_misc.append(line)
                    except:
                        pass
                    try:
                        if line.proj_note_surface.strip():
                            notes_surface.append(line)
                    except:
                        pass
                    
                if len(impnotes) == 1:
                    impnotes_text = impnotes[0].proj_impnote.strip()
                elif len(impnotes) > 1:
                    for l in impnotes:
                        if impnotes_text:
                            impnotes_text += '||' # add our custom line break symbols at the beginning if not empty
                        try:
                            impnotes_text += f'{l.proj_line1.strip()}: {l.proj_impnote.strip()}'
                        except:
                            pass
                if len(notes_cadnc) == 1:
                    note_cadnc_text = notes_cadnc[0].proj_note_cadnc.strip()
                elif len(notes_cadnc) > 1:
                    for l in notes_cadnc:
                        if note_cadnc_text:
                            note_cadnc_text += '||' # add our custom line break symbols at the beginning if not empty
                        try:
                            note_cadnc_text += f'{l.proj_line1.strip()}: {l.proj_note_cadnc.strip()}'
                        except:
                            pass
                if len(notes_laser) == 1:
                    note_laser_text = notes_laser[0].proj_note_laser.strip()
                elif len(notes_laser) > 1:
                    for l in notes_laser:
                        if note_laser_text:
                            note_laser_text += '||' # add our custom line break symbols at the beginning if not empty
                        try:
                            note_laser_text += f'{l.proj_line1.strip()}: {l.proj_note_laser.strip()}'
                        except:
                            pass
                if len(notes_bend) == 1:
                    note_bend_text = notes_bend[0].proj_note_bend.strip()
                elif len(notes_bend) > 1:
                    for l in notes_bend:
                        if note_bend_text:
                            note_bend_text += '||' # add our custom line break symbols at the beginning if not empty
                        try:
                            note_bend_text += f'{l.proj_line1.strip()}: {l.proj_note_bend.strip()}'
                        except:
                            pass
                if len(notes_misc) == 1:
                    note_misc_text = notes_misc[0].proj_note_misc.strip()
                elif len(notes_misc) > 1:
                    for l in notes_misc:
                        if note_misc_text:
                            note_misc_text += '||' # add our custom line break symbols at the beginning if not empty
                        try:
                            note_misc_text += f'{l.proj_line1.strip()}: {l.proj_note_misc.strip()}'
                        except:
                            pass
                if len(notes_surface) == 1:
                    note_surface_text = notes_surface[0].proj_note_surface.strip()
                elif len(notes_surface) > 1:
                    for l in notes_surface:
                        if note_surface_text:
                            note_surface_text += '||' # add our custom line break symbols at the beginning if not empty
                        try:
                            note_surface_text += f'{l.proj_line1.strip()}: {l.proj_note_surface.strip()}'
                        except:
                            pass
                return (line0_text,
                        line2_text,
                        impnotes_text,
                        note_cadnc_text,
                        note_laser_text,
                        note_bend_text,
                        note_misc_text,
                        note_surface_text,
                        )
            
            # decide wether lines need merging or not for project sheets
            for line in sorted_lines[1:]:
                if (line.folder_no == next_sheet.folder_no and
                    line.folder_subno == next_sheet.folder_subno and
                    line.material == next_sheet.material and
                    line.material_extra == next_sheet.material_extra and
                    line.material_surface == next_sheet.material_surface and
                    line.sheet_thickness == next_sheet.sheet_thickness and
                    line.due_date == next_sheet.due_date and
                    line.due_date_postfix == next_sheet.due_date_postfix):
                    # this line matches the next line to be added so append data
                    next_lines.append(line)
                else:
                    # we need a new sheet, so append the current one after finishing merges
                    (line0_text, line2_text, proj_impnotes, proj_note_cadnc, proj_note_laser, proj_note_bend, proj_note_misc, proj_note_surface) = merge_lines(next_lines)
                    merged_lines.append((next_sheet, line0_text, next_lines, line2_text,
                                         proj_impnotes,
                                         proj_note_cadnc, proj_note_laser, proj_note_bend, proj_note_misc, proj_note_surface)) # append the last line
                    next_sheet= line # the current line is now the next one
                    next_lines = [next_sheet, ]
            # Important: append the last line
            (line0_text, line2_text, proj_impnotes, proj_note_cadnc, proj_note_laser, proj_note_bend, proj_note_misc, proj_note_surface) = merge_lines(next_lines)
            merged_lines.append((next_sheet, line0_text, next_lines, line2_text,
                                 proj_impnotes,
                                 proj_note_cadnc, proj_note_laser, proj_note_bend, proj_note_misc, proj_note_surface)) # append the last line
            return merged_lines
        
        context['get_project_sheets'] = get_project_sheets
        return context
            
class SaleContact(ModelSQL):
    "Sale - Contact"
    __name__ = 'party.party-sale.sale'
    # 6.6 changes from slect to selectors means removing  select='True" 
    sale = fields.Many2One('sale.sale', "Sale", ondelete='CASCADE', required=True)
    party = fields.Many2One('party.party', "Contact", ondelete='CASCADE', required=True)
                    
            

class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    # extra fields
    real_product = fields.Boolean('Real product',
                                  states = { 'invisible': True, },
                                  help = 'this gets set if data is filled in from an actual product')
    folder_no = fields.Integer('Folder number',
                               required = True,
                               states = { 'readonly': (~Eval('sale_state').in_(['draft', 'quotation'])),
                               },
                               help = 'Folder number')
    folder_subno = fields.Char('Subfolder',
                               states = { 'readonly': ((~Eval('sale_state').in_(['draft', 'quotation'])) |
                                                       Eval('folder_skip') |
                                                       Eval('real_product')),
                               },
                               help = 'Subfolder number (letter)')
    folder_submax = fields.Char('Subfolder maximum',
                                states = { 'readonly': ((~Eval('sale_state').in_(['draft', 'quotation'])) |
                                                        Eval('folder_skip') |
                                                        Eval('real_product')),
                                },
                                help = 'Subfolder maximum')
    folder_skip = fields.Boolean('Skip this on project sheets',
                                 states = { 'readonly': (~Eval('sale_state').in_(['draft', 'quotation'])),
                                 },
                                 help = 'if selected this sale line will not show on project sheets')
    due_date = fields.Date('Due date',
                           states = { 'readonly': ~Eval('sale_state').in_(['draft', 'quotation']), },
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
    proj_note_cadnc = fields.Text('Project notes - CAD/NC',
                               states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                      Eval('real_product')),
                               },
                               help = 'production notes for CAD/NC')
    proj_note_laser = fields.Text('Project notes - laser cutting',
                                  states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                         Eval('real_product')),
                                            },
                                  help = 'production notes for laser cutting')
    proj_note_bend = fields.Text('Project notes - bending',
                                 states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                        Eval('real_product')),
                                           },
                                 help = 'production notes for bending')
    proj_note_misc = fields.Text('Project notes - Misc (welding, drilling, countersink, thread cutting, ..)',
                                 states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                        Eval('real_product')),
                                           },
                                 help = 'production notes for welding, drilling, countersink, thread cutting, ..')
    proj_note_surface = fields.Text('Project notes - surface treatments',
                                    states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                           Eval('real_product')),
                                              },
                                    help = 'production notes for surface treatments')
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
                              states = { 'readonly': (~Eval('sale_state').in_(['draft', 'quotation'])),
                              },
                              help = 'if selected this sale line will not show on invoices or delivery notes')
    
    inv_line0 = fields.Char('Invoice / delivery note line 0',
                             states = {
                                 'readonly': ((~Eval('sale_state').in_(['draft', 'quotation'])) |
                                              Eval('inv_line0_skip') |
                                              Eval('inv_skip') |
                                              Eval('real_product')
                                 ),
                             },
                             help = 'above first line on the invoice / delivery note generated for this sale line.')
    inv_line0_skip = fields.Boolean('Skip invoice / delivery note line 0',
                                    states = {'readonly': ((~Eval('sale_state').in_(['draft', 'quotation'])) |
                                                           Eval('inv_skip') |
                                                           Eval('real_product')),
                                    },
                                    help = 'if selected invoice line 0 will be ignored')
    inv_line1 = fields.Char('Invoice / delivery note line 1',
                             states = {
                                 'readonly': ((~Eval('sale_state').in_(['draft', 'quotation'])) |
                                              Eval('inv_skip') |
                                              Eval('real_product')),
                             },
                             help = 'first line on the invoice / delivery note generated for this sale line')
    inv_line2 = fields.Char('Invoice / delivery note line 2',
                             states = {
                                 'readonly': ((~Eval('sale_state').in_(['draft', 'quotation'])) |
                                              Eval('inv_line2_skip') |
                                              Eval('inv_skip') |
                                              Eval('real_product')),
                             },
                             help = 'second line on the invoice / delivery note generated for this sale line')
    inv_line2_skip = fields.Boolean('Skip invoice / delivery note line 2',
                                    states = {'readonly': ((~Eval('sale_state').in_(['draft', 'quotation'])) |
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
                raise UserError(f'Produkte ohne Projektzeile 1 können nicht hinzugefügt werden: Pos {self.sequence}:\n{self.product}')
            self.proj_line1 = self.product.proj_line1
            self.proj_line2 = self.product.proj_line2
            self.proj_note_cadnc = self.product.proj_note_cadnc
            self.proj_note_laser = self.product.proj_note_laser
            self.proj_note_bend = self.product.proj_note_bend
            self.proj_note_misc = self.product.proj_note_misc
            self.proj_note_surface = self.product.proj_note_surface
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

    def get_move(self, shipment_type):
        move = super().get_move(shipment_type)
        # logger.info(move)
        if move:
            move.on_change_origin()
        return move

    def get_invoice_line(self):
        inv_line = super().get_invoice_line()
        # try to call custom on_change_origin
        try:
            inv_line[0].on_change_origin()
        except:
            # was not InvoiceLine, it seems..
            # (cannot use isinstance here cuz of circular imports, also doing nothing is fine in this case 
            pass
        return inv_line
            
class AmendmentLine(metaclass=PoolMeta):
    __name__ = 'sale.amendment.line'
    # extra fields
    real_product = fields.Boolean('Real product',
                                  states = { 'invisible': True, },
                                  help = 'this gets set if data is filled in from an actual product')
    folder_no = fields.Integer('Folder number',
                               #required = True,
                               states = { 'readonly': Eval('folder_skip') & True,
                                          'invisible': Eval('action') != 'line',
                               },
                               help = 'Folder number')
    folder_subno = fields.Char('Subfolder',
                               states = { 'readonly': (Eval('folder_skip') |
                                                       Eval('real_product')),
                                          'invisible': Eval('action') != 'line',
                               },
                               help = 'Subfolder number (letter)')
    folder_submax = fields.Char('Subfolder maximum',
                                states = { 'readonly': (Eval('folder_skip') |
                                                        Eval('real_product')),
                                           'invisible': Eval('action') != 'line',
                                },
                                help = 'Subfolder maximum')
    folder_skip = fields.Boolean('Skip this on project sheets',
                                 states = { 'readonly': Eval('real_product') & True,
                                            'invisible': Eval('action') != 'line',
                                 },
                                 help = 'if selected this sale line will not show on project sheets')
    due_date = fields.Date('Due date',
                           states = { 'invisible': Eval('action') != 'line',
                                     },
                           help = 'Due date for this sale line (replaces due date from project sheet)')

    due_date_postfix = fields.Char('Due date extra',
                                   states = { 'invisible': Eval('action') != 'line',},
                                   help = 'Extra text for due date for this sale line (replaces due date extra from project sheet ')
    proj_line0 = fields.Char('Project sheet line 0',
                             states = { 'readonly': Eval('real_product') & True,
                                        'invisible': Eval('action') != 'line',
                             },
                             help = 'above first line on the project sheets generated for this sale line')
    proj_line1 = fields.Char('Project sheet line 1',
                             #required = True,
                             states = { 'readonly': Eval('real_product') & True,
                                        'invisible': Eval('action') != 'line',
                             },
                             help = 'second line on the project sheets generated for this sale line')
    proj_line2 = fields.Char('Project sheet line 2',
                             states = { 'readonly': Eval('real_product') & True,
                                        'invisible': Eval('action') != 'line',
                             },
                             help = 'second line on the project sheets generated for this sale line')
    proj_impnote = fields.Char('Project important notes',
                               states = {'readonly': Eval('real_product') & True,
                                         'invisible': Eval('action') != 'line',
                               },
                               help = 'important production notes')
    proj_note_cadnc = fields.Text('Project notes - CAD/NC',
                               states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                      Eval('real_product')),
                                         'invisible': Eval('action') != 'line',
                               },
                               help = 'production notes for CAD/NC')
    proj_note_laser = fields.Text('Project notes - laser cutting',
                                  states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                         Eval('real_product')),
                                            'invisible': Eval('action') != 'line',
                                            },
                                  help = 'production notes for laser cutting')
    proj_note_bend = fields.Text('Project notes - bending',
                                 states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                        Eval('real_product')),
                                           'invisible': Eval('action') != 'line',
                                           },
                                 help = 'production notes for bending')
    proj_note_misc = fields.Text('Project notes - Misc (welding, drilling, countersink, thread cutting, ..)',
                                 states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                        Eval('real_product')),
                                           'invisible': Eval('action') != 'line',
                                           },
                                 help = 'production notes for welding, drilling, countersink, thread cutting, ..')
    proj_note_surface = fields.Text('Project notes - surface treatments',
                                    states = {'readonly': ((Eval('sale_state') != 'draft') |
                                                           Eval('real_product')),
                                              'invisible': Eval('action') != 'line',
                                              },
                                    help = 'production notes for surface treatments')
    material = fields.Char('Material',
                           states = {'readonly': (Eval('product') |
                                                  Eval('real_product')),
                                     'invisible': Eval('action') != 'line',
                           },
                           help = 'Material name (auto-filled from product)')
    # those 2 are not usually set on the product (at least not for now so leave them read-write
    # TODO: maybe make them readonly only if values were set from the product
    material_extra = fields.Char('Material extra text',
                                 states = { 'readonly': Eval('real_product') & True,
                                            'invisible': Eval('action') != 'line',
                                 },
                                 #states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                                 help = 'extra text to be appended to material')
    material_surface = fields.Char('Material surface',
                                   states = { 'readonly': Eval('real_product') & True,
                                              'invisible': Eval('action') != 'line',
                                   },
                                   #states = {'readonly': (Eval('sale_state') != 'draft') | Eval('product'), },
                                   help = 'surface treatment for material (paint,..) ')
    # this is actually also used for non sheet metal thickness, but not going to rename the field, just changing the description
    sheet_thickness = fields.Float('Material thickness',
                                   states = {'readonly': (Eval('product') |
                                                          Eval('real_product')),
                                             'invisible': Eval('action') != 'line',
                                   },
                                   digits = (2, 2),
                                   help = 'material thickness')
    
    # extra fields for delivery notes / invoices (where it does not match the normal lines)
    # line(s)

    inv_skip = fields.Boolean('Skip this whole sale line for invoice / delivery note',
                              states = { 'readonly': Eval('real_product') & True,
                                         'invisible': Eval('action') != 'line',
                              },
                              help = 'if selected this sale line will not show on invoices or delivery notes')
    
    inv_line0 = fields.Char('Invoice / delivery note line 0',
                             states = {
                                 'readonly': (Eval('inv_line0_skip') |
                                              Eval('inv_skip') |
                                              Eval('real_product')
                                 ),
                                 'invisible': Eval('action') != 'line',
                             },
                             help = 'above first line on the invoice / delivery note generated for this sale line.')
    inv_line0_skip = fields.Boolean('Skip invoice / delivery note line 0',
                                    states = {'readonly': (Eval('inv_skip') |
                                                           Eval('real_product')),
                                              'invisible': Eval('action') != 'line',
                                    },
                                    help = 'if selected invoice line 0 will be ignored')
    inv_line1 = fields.Char('Invoice / delivery note line 1',
                             states = {
                                 'readonly': (Eval('inv_skip') |
                                              Eval('real_product')),
                                 'invisible': Eval('action') != 'line',
                             },
                             help = 'first line on the invoice / delivery note generated for this sale line')
    inv_line2 = fields.Char('Invoice / delivery note line 2',
                             states = {
                                 'readonly': (Eval('inv_line2_skip') |
                                              Eval('inv_skip') |
                                              Eval('real_product')),
                                 'invisible': Eval('action') != 'line',
                             },
                             help = 'second line on the invoice / delivery note generated for this sale line')
    inv_line2_skip = fields.Boolean('Skip invoice / delivery note line 2',
                                    states = {'readonly': (Eval('inv_skip') |
                                                           Eval('real_product')),
                                              'invisible': Eval('action') != 'line',
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

    @classmethod
    def default_proj_line1(cls):
        # return empty string here in case there are already invoices cuz NOT NULL
        return ' '
    
    @fields.depends('material', 'material_extra', 'sheet_thickness', 'material_surface', 'real_product', 'folder_skip')
    def on_change_product(self):
        # TODO: set material and sheet_thickness as readonly normally and only allow overwriting if no product is set?
        try:
            super().on_change_product()
        except AttributeError:
            pass
        if not hasattr(self, 'product'):
            return
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
            self.proj_note_cadnc = self.product.proj_note_cadnc
            self.proj_note_laser = self.product.proj_note_laser
            self.proj_note_bend = self.product.proj_note_bend
            self.proj_note_misc = self.product.proj_note_misc
            self.proj_note_surface = self.product.proj_note_surface
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

    @fields.depends('line')
    def on_change_line(self):
        super().on_change_line()
        if self.line:
            self.real_product = self.line.real_product
            self.folder_no = self.line.folder_no
            self.folder_subno = self.line.folder_subno
            self.folder_submax = self.line.folder_submax
            self.folder_skip = self.line.folder_skip
            self.due_date = self.line.due_date
            self.due_date_postfix = self.line.due_date_postfix
            self.proj_line0 = self.line.proj_line0
            self.proj_line1 = self.line.proj_line1
            self.proj_line2 = self.line.proj_line2
            self.proj_impnote = self.line.proj_impnote
            self.material = self.line.material
            self.material_extra = self.line.material_extra
            self.material_surface = self.line.material_surface
            self.sheet_thickness = self.line.sheet_thickness
            self.inv_skip = self.line.inv_skip
            self.inv_line0 = self.line.inv_line0
            self.inv_line1 = self.line.inv_line1
            self.inv_line2 = self.line.inv_line2
            self.inv_line2_skip = self.line.inv_line2_skip
            
    def _apply_line(self, sale, sale_line):
        super()._apply_line(sale, sale_line)
        sale_line.real_product = self.real_product
        sale_line.folder_no = self.folder_no
        sale_line.folder_subno = self.folder_subno
        sale_line.folder_submax = self.folder_submax
        sale_line.folder_skip = self.folder_skip
        sale_line.due_date = self.due_date
        sale_line.due_date_postfix = self.due_date_postfix
        sale_line.proj_line0 = self.proj_line0
        sale_line.proj_line1 = self.proj_line1
        sale_line.proj_line2 = self.proj_line2
        sale_line.proj_impnote = self.proj_impnote
        sale_line.material = self.material
        sale_line.material_extra = self.material_extra
        sale_line.material_surface = self.material_surface
        sale_line.sheet_thickness = self.sheet_thickness
        sale_line.inv_skip = self.inv_skip
        sale_line.inv_line0 = self.inv_line0
        sale_line.inv_line1 = self.inv_line1
        sale_line.inv_line2 = self.inv_line2
        sale_line.inv_line2_skip = self.inv_line2_skip
