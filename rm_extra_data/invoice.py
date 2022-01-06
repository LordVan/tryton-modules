from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
#from trytond.modules.company.model import (
#        employee_field, set_employee, reset_employee)
from trytond.exceptions import UserWarning, UserError

import logging
logger = logging.getLogger(__name__)

__all__ = ['InvoiceReport']


class InvoiceReport(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def get_context(cls,records, header, data):
        context = super(InvoiceReport, cls).get_context(records, header, data)
        #context['testdata'] = 'This is just some testdata to make sure things work ok'
        logger.info(context['record'])
        logger.info(context.keys())
        return context
