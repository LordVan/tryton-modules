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

__all__ = ['InvoiceLine', 'InvoiceReport']


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'

    line0 = fields.Char('Invoice line 0')
    line1 = fields.Char('Invoice line 1')
    line2 = fields.Char('invoice line 2')
    skip = fields.Boolean('Skip this line on invoices')

    @fields.depends('origin')
    def on_change_origin(self):
        # copy line0,1,2 from SaleLine or Moves
        if isinstance(self.origin, SaleLine):
            moves = self.origin.moves
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
        #context['testdata'] = 'This is just some testdata to make sure things work ok'
        # logger.info(context.keys())
        # for line in context['invoice'].lines:
        #     logger.info(line)
        filtered_lines = list(records[0].lines)
        #list(filter(lambda x:x.origin.inv_skip == False, records[0].lines))
        # do not skip them yet here in case the amounts are not zero !!
        filtered_lines.sort(key=lambda x: (x.origin.sale, x.origin.sequence))
        sales = []
        for fl in filtered_lines:
            if fl.origin.sale not in sales:
                sales.append(fl.origin.sale)
        logger.info('sales: ' + str(sales))
        sorted_lines = []
        for sale in sales:
            # WARNING: make sure skipped items never have a price so subtotal and total match!!
            sale_lines = list(filter(lambda x: ((x.origin.inv_skip == False) &
                                                (x.origin.sale == sale)),
                                     records[0].lines))
            delnotes = []
            for sl in sale_lines:
                if sl.origin and sl.origin.moves:
                    logger.info(delnotes)
                    delnotes = delnotes + list(sl.origin.moves)
            sorted_lines.append({'sale': sale,
                                 'sale_date': sale.sale_date,
                                 'sale_number': sale.number,
                                 'commission': sale.description,
                                 'reference': sale.reference,
                                 'offer_nr': sale.offer_number,
                                 'offer_date': sale.offer_date,
                                 'delivery_notes': delnotes,
                                 'inv_lines': sale_lines})
        context['sorted_lines'] = sorted_lines
#         for sl in sorted_lines:
#             logger.info(f'''Sale number: {sl['sale_number']}
# Sale date: {sl['sale_date']}
# Commission: {sl['commission']}
# Reference: {sl['reference']}
# Offer number: {sl['offer_nr']}
# Offer date: {sl['offer_date']}
# lines: {sl['inv_lines']}''')
        return context
