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
    __name__ = 'stock.shipment.out.delivery_note'

    @classmethod
    def get_context(cls, records, header, data):
        context = super(DeliveryNote, cls).get_context(records, header, data)
        # first filter, then sort the move lines (we only want delivery notes for
        # individual sales, so no need to sort by sale, but just in case adding it

        mySale = None
        # get all the lines we want to display
        if records[0].state in ('picked', 'packed', 'done'):
            filtered_lines = [x for x in records[0].outgoing_moves if not x.skip]
            # get lines with an origin
            sorted_lines = [x for x in filtered_lines if x.origin]
            mySale = sorted_lines[0].origin.sale
        else:
            # if we are not in picked, packed or done states use inventory moves for report to preview
            filtered_lines = [x for x in records[0].inventory_moves if not x.skip]
            # get lines with an origin
            sorted_lines = [x for x in filtered_lines if x.origin]
            mySale = sorted_lines[0].origin.sale
            if not mySale:
                # no origin sale found on inventory moves (for whatever reason)
                # try outgoing moves to see if we find an origin sale
                out_mov = [x for x in records[0].outgoing_moves if not x.skip]
                out_mov_sorted =  [x for x in out_mov  if x.origin]
                mySale = out_mov_sorted[0].origin.sale

        # we need one sale associated at least so this never be empty but
        if not mySale:
            raise UserError('Kein Verkauf gefunden! Es muss mindestens eine Zeile mit Verkaufs-Herkunft geben')

        context['sale'] = mySale
        no_origin_lines = [x for x in filtered_lines if not x.origin] # manually added lines without origin
        try:
            sorted_lines.sort(key=lambda x: (x.origin.sale, x.origin.sequence))
        except:
            # if this fails (due to missing origin,..) ignore sorting
            # this should not happen anymore but keeping just in case
            pass
        # add lines without origin again
        sorted_lines += no_origin_lines
        context['sorted_lines'] = sorted_lines

        if not records[0].effective_date:
            raise UserError('Effektives Datum nicht ausgewählt!')

        # some debugging
        # import pprint
        # pp = pprint.PrettyPrinter(indent=4)
        # context['testdata'] = pp.pformat(context)
        # logger.info(context['record'])
        return context

class Move(metaclass=PoolMeta):
    "Stock move with custom fields"
    __name__ = 'stock.move'

    line0 = fields.Char('Delivery note line 0')
    line1 = fields.Char('Delivery note line 1')
    line2 = fields.Char('Delivery note line 2')
    skip = fields.Boolean('Skip this on delivery notes')

    # FIXME: should i add the line fields here too?..
    @fields.depends('origin')
    def on_change_origin(self):
        # gets line0,1,2 from self.origin if it is a SaleLine
        # WARNING: overwrites without checkinf if non-empty (but that shouldn't be an issue)
        # TODO: decide if we should or should not strip the lines first
        if isinstance(self.origin, SaleLine) :
            #logger.debug('copying lines from sale line')
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
            if self.origin.inv_skip:
                # do it this way as some older entries could have NULL set in the DB!
                self.skip = True
            else:
                self.skip = False
        elif isinstance(self.origin, Move):
            # this is based on another move
            #logger.debug('copying from another move')
            # no need to check if we are copying from another move (same class) anyway
            self.line0 = self.origin.line0
            self.line1 = self.origin.line1
            self.line2 = self.origin.line2
            self.skip = self.origin.skip

class ShipmentOut(metaclass=PoolMeta):
    "ShipmentOut with custom fields"
    __name__ = 'stock.shipment.out'

    sale_refs = fields.Char('Sale references',
                            states = {'readonly': ~Eval('state').in_(['draft', 'waiting']),},
                            help = 'Sale references copied from sale')

    # do not use a function field here as it could be an issue performance wise on large lists
    # sale_refs = fields.Function(fields.Char('References'), 'get_sale_references')

    # def get_sale_references(self, name):
    #     ref = 'lala'
    #     sales = []
    #     # for move in self.get_outgoing_moves(''):
    #     #     if isinstance(move.origin, SaleLine):
    #     #         pass
    #     return ref

    def _get_inventory_move(self, incoming_move):
        move = super()._get_inventory_move(incoming_move)
        if move:
            # do not throw an exception if for some reason there is no move associated
            logger.warning(f'Could not get inventory move for {incoming_move} (shipment: {self})')
            move.on_change_origin()
        return move

    def _sync_move_key(self, move):
        '''
        Make sure to sync (potentially) fixed line0,1,2, and skip to outgoing moves
        '''
        ret = super()._sync_move_key(move)
  #       logger.info('stock.ShipmentOut._sync_move_key ### %s', self)
  #       logger.info(f'############# {ret}')
  #       logger.info(f'''##### Move ({move})
  # line0: {move.line0}
  # line1: {move.line1}
  # line2: {move.line2}
  # skip: {move.skip}
  # origin: {move.origin}''')
        return ret + (('line0', move.line0),
                      ('line1', move.line1),
                      ('line2', move.line2),
                      ('skip', move.skip),
                      )
    @classmethod
    @ModelView.button
    @Workflow.transition('packed')
    @set_employee('packed_by')
    def pack(cls, shipments):
        for shipment in shipments:
            if not shipment.effective_date:
                raise UserError('Effektives Datum nicht ausgewählt!')
        super().pack(shipments)
