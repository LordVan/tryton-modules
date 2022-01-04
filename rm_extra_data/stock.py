from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)
from trytond.exceptions import UserWarning, UserError

from .sale import SaleLine

import logging
logger = logging.getLogger(__name__)

__all__ = ['DeliveryNote', 'Move']

class DeliveryNote(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.delivery_note.rm'

    @classmethod
    def get_context(cls, records, header, data):
        context = super(DeliveryNote, cls).get_context(records, header, data)
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        context['testdata'] = pp.pformat(context)
        logger.info(context['record'])
        return context

class Move(metaclass=PoolMeta):
    "Stock move with custom fields"
    __name__ = 'stock.move'

    line0 = fields.Char('Delivery note line 0')
    line1 = fields.Char('Delivery note line 1')
    line2 = fields.Char('Delivery note line 2')
    skip = fields.Boolean('Skip this on delivery notes and invoices')

    @fields.depends('origin')
    def on_change_origin(self):
        # gets line0,1,2 from self.origin if it is a SaleLine
        # WARNING: overwrites without checkinf if non-empty (but that shouldn't be an issue)
        # TODO: decide if we should or should not strip the lines first
        if isinstance(self.origin, SaleLine) :
            logger.debug('copying lines from sale line')
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
        elif isinstance(self.origin, Move):
            # this is based on another move
            logger.debug('copying from another move')
            # no need to check if we are copying from another move (same class) anyway
            self.line0 = self.origin.line0
            self.line1 = self.origin.line1
            self.line2 = self.origin.line2
            self.skip = self.origin.skip

class ShipmentOut(metaclass=PoolMeta):
    "ShipmentOut with custom fields"
    __name__ = 'stock.shipment.out'

    def _get_inventory_move(self, incoming_move):
        move = super()._get_inventory_move(incoming_move)
        move.on_change_origin()
        return move
