from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool
from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, sequence_ordered
from trytond.modules.company.model import (
        employee_field, set_employee, reset_employee)

__all__ = ['Sale']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    # extra fields:

    reference_com = fields.Char('Commission', select = True)
    
    dolibarr_pid = fields.Integer('Dolibarr project id',
                                  #readonly = True,
                                  help = 'project id from dolibarr (for import purposes only)')


    # extra_contacts = fields.Many2Many('sale.sale-party.party',
    #                                   'party',
    #                                   'party',
    #                                   'Extra contacts')


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
                               help = 'Folder number')
    folder_subcount = fields.Integer('Folder sub count',
                                     required = True,
                                     help = 'subfolder count')
