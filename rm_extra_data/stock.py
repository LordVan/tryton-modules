from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)
from trytond.exceptions import UserWarning, UserError

__all__ = ['DeliveryNote']

class DeliveryNote(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out.delivery_note.rm'

    @classmethod
    def get_context(cls, records, header, data):
        context = super(DeliveryNote, cls).get_context(records, header, data)
        context['testdata'] = str(context)
        return context
