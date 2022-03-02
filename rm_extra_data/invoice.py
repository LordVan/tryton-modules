from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
#from trytond.modules.company.model import (
#        employee_field, set_employee, reset_employee)
from trytond.exceptions import UserWarning, UserError
#from trytond.modules.account_invoice.invoice import InvoiceLine

from .sale import SaleLine

import logging
logger = logging.getLogger(__name__)

__all__ = ['InvoiceLine', 'InvoiceReport', 'Invoice']


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    performance_period = fields.Char('Performance period',
                                     # required = True,
                                     states = { 'readonly': ~Eval('state').in_(['draft', 'validated']) })

    @classmethod
    def default_performance_period(cls):
        return ''

class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'

    line0 = fields.Char('Invoice line 0')
    line1 = fields.Char('Invoice line 1')
    line2 = fields.Char('Invoice line 2')
    skip = fields.Boolean('Skip this line on invoices')
    hide_unit_price = fields.Boolean('Hide unit price on invoice')

    @classmethod
    def default_skip(cls):
        return False

    @classmethod
    def default_hide_unit_price(cls):
        return False

    @fields.depends('product', 'unit', '_parent_invoice.type',
                    '_parent_invoice.party', 'party', 'invoice', 'invoice_type',
                    '_parent_invoice.invoice_date', '_parent_invoice.accounting_date',
                    'company',
                    methods=['_get_tax_rule_pattern'])
    def on_change_product(self):
        super().on_change_product()
        if not self.product:
            return
        # purposely ignore the "do not show on delivery note / invoice flag here
        # since we are obviously adding this on purpose and there is no reason
        # to add anything to an invoice we do not want on it that I can think of
        if not self.product.inv_line0_skip:
            if self.product.inv_line0 and self.product.inv_line0.strip():
                self.line0 = self.product.inv_line0
            elif self.product.proj_line0 and self.product.proj_line0:
                self.line0 = self. product.proj_line0
        if self.product.inv_line1 and self.product.inv_line1.strip():
            self.line1 = self.product.inv_line1
        elif self.product.proj_line1 and self.product.proj_line1:
            self.line1 = self. product.proj_line1
        if not self.product.inv_line2_skip:
            if self.product.inv_line2 and self.product.inv_line2.strip():
                self.line2 = self.product.inv_line2
            elif self.product.proj_line2 and self.product.proj_line2:
                self.line2 = self. product.proj_line2


    @fields.depends('origin')
    def on_change_origin(self):
        # copy line0,1,2 from SaleLine or Moves
        if isinstance(self.origin, SaleLine):
            try:
                moves = self.origin.moves
            except:
                # something went wrong getting the moves.. doing nothing here
                return
            logger.info('%s ### moves found: %s', self, moves)
            if not moves:
                logger.info('%s ### no moves found .. copy from sale line', self)
                if not self.origin.inv_line0_skip:
                    if self.origin.inv_line0:
                        self.line0 = self.origin.inv_line0
                    elif self.origin.proj_line0:
                        self.line0 = self.origin.proj_line0
                if self.origin.inv_line1.strip():
                    self.line1 = self.origin.inv_line1
                else:
                    # no need to check here cuz proj_line1 is required on sale lines for us
                    self.line1 = self.origin.proj_line1
                if not self.origin.inv_line2_skip:
                    if self.origin.inv_line2:
                        self.line2 = self.origin.inv_line2
                    elif self.origin.proj_line2:
                        self.line2 = self.origin.proj_line2
                self.skip = self.origin.inv_skip
            else:
                if len(moves) != 1:
                    logger.info('%s ### More than one move per invoice line. Taking the lines from the last one', self)
                    moves.sort(key=lambda x: x.id) # id is fine as we are using it for now and sorting is faster that way
                    logger.info('%s ### moves after sorting: %s', self, moves)
                self.line0 = moves[-1].line0
                self.line1 = moves[-1].line1
                self.line2 = moves[-1].line2
                self.skip = moves[-1].skip


class InvoiceReport(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def get_context(cls, records, header, data):
        context = super(InvoiceReport, cls).get_context(records, header, data)

        # Warning = Pool().get('res.user.warning')
        
        # get and sort invoice lines by sale and origin sequence
        # first filter out lines that have no origins
        filtered_lines = list(filter(lambda x: (x.origin), records[0].lines))
        # get the invoice lines that do not have an origin and are to be shown on the report
        no_origin_lines = list(filter(lambda x: (not x.origin and not x.skip), records[0].lines))
        # Then] sort
        filtered_lines.sort(key=lambda x: (x.origin.sale, x.origin.sequence))
        # logger.info('inv. lines sorted: ' + str(filtered_lines))

        #get a list of the different sales included in this invoice
        sales = []
        for fl in filtered_lines:
            if fl.origin.sale not in sales:
                sales.append(fl.origin.sale)

        sorted_lines = [] # this will hold our final invoice lines for the report
        for sale in sales:
            # WARNING: make sure skipped items never have a price so subtotal and total match!!
            # get all invoice lines for the first sale and filter out skipped ones
            invoice_lines = list(filter(lambda x: ((x.skip == False) &
                                                (x.origin.sale == sale)),
                                     filtered_lines))
            # logger.info('inv. lines for sale: ' + str(invoice_lines))
            my_invoice_lines = []
            delnotes = []
            shipment_numbers = []
            delnotes_text = ''
            for il in invoice_lines:
                # first get delivery notes if we have some and append to sale
                if il.origin and il.origin.moves:
                    logger.info(delnotes)
                    delnotes = delnotes + list(il.origin.moves)
                for move in delnotes:
                    if move.shipment.number not in shipment_numbers:
                        shipment_numbers.append(move.shipment.number)
                # then make our custom invoice line array of dicts
                # check if we got this origin line already:
                # TODO: deal with split positions,..
                #il_exists = next((i for i, item in enumerate(my_invoice_lines) if item['origin'] == il.origin
                my_il = {}
                my_il['il_original'] = il # just in case we need something not in the dict
                my_il['origin'] = il.origin # the sale line
                my_il['quantity'] = il.quantity
                my_il['unit_price'] = il.unit_price
                my_il['hide_unit_price'] = il.hide_unit_price
                # TODO: fix amount for merged lines
                my_il['line_amount'] = il.amount #il.unit_price * il.quantity # just calculate here for simplicity
                my_il['currency'] = il.currency
                my_il['taxes_deductible_rate'] = il.taxes_deductible_rate
                my_il['unit'] = il.unit
                if il.line0:
                    my_il['line0'] = il.line0.strip()
                else:
                    my_il['line0'] = ''
                my_il['line1'] = il.line1.strip()
                if il.line2:
                    my_il['line2'] = il.line2.strip()
                else:
                    my_il['line2'] = ''
                my_invoice_lines.append(my_il)
            # sort out deliver note text here cuz it is so much easier:
            shipment_numbers.sort() # sort it in order
            sn_l = list(set(shipment_numbers)) # use conversion to set to make sure it is a unique list
            sn_l.sort()
            delnotes_text = ', '.join(sn_l) 
            if not records[0].performance_period:
                raise UserError('Leistungszeitraum nicht angegeben!')
            sorted_lines.append({'sale': sale,
                                 'sale_date': sale.sale_date,
                                 'sale_number': sale.number,
                                 'commission': sale.description,
                                 'reference': sale.reference,
                                 'offer_nr': sale.offer_number,
                                 'offer_date': sale.offer_date,
                                 'delivery_notes': delnotes,
                                 'delivery_notes_text': delnotes_text,
                                 'inv_lines': my_invoice_lines})
        for il in no_origin_lines:
            # deal with lines without origin so we can add things if needed that were not expected at sale time
            # setup costs, delivery, extra work time ...           
            my_il = {}
            my_il['il_original'] = il
            my_il['origin'] = None
            my_il['quantity'] = il.quantity
            my_il['unit_price'] = il.unit_price
            my_il['hide_unit_price'] = il.hide_unit_price
            # TODO: fix amount for merged lines
            my_il['line_amount'] = il.amount #il.unit_price * il.quantity # just calculate here for simplicity
            my_il['currency'] = il.currency
            my_il['taxes_deductible_rate'] = il.taxes_deductible_rate
            my_il['unit'] = il.unit
            if il.line0:
                my_il['line0'] = il.line0.strip()
            else:
                my_il['line0'] = ''
            my_il['line1'] = il.line1.strip()
            if il.line2:
                my_il['line2'] = il.line2.strip()
            else:
                my_il['line2'] = ''

            # append it to the last line of the last sale
            sorted_lines[-1]['inv_lines'].append(my_il)
        

#         for sl in sorted_lines:
#             logger.info(f'''Sale number: {sl['sale_number']}
# Sale date: {sl['sale_date']}
# Commission: {sl['commission']}
# Reference: {sl['reference']}
# Offer number: {sl['offer_nr']}
# Offer date: {sl['offer_date']}
# lines: {sl['inv_lines']}''')

        context['sorted_lines'] = sorted_lines
        return context
