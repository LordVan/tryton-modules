from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool

__all__ = ['Party', 'Replace']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'
    
    # custom stuff for us
    # unique could be added by adding sql constraints - see __setup__ in party module party.py
    customer_no = fields.Char('Customer number',
                              size = 9)
    supplier_no = fields.Char('Supplier number',
                              size = 9)
    pn_name = fields.Char('PN name',
                          size = 50)
    # TODO: automatically capitalize this here or through view?
    legal_name = fields.Char('Legal name',
                             help = 'Legally correct name')
    salutation = fields.Char('Salutation',
                             size = 50) # limiting length since more seems useless
    inv_name_line1 = fields.Char('Invoice name line 1',
                                 help = 'Invoice customer name line 1'
                                 )
    inv_name_line2 = fields.Char('Invoice name line 2',
                                 help = 'Invoice customer name line 2'
                                 )
    sale_note = fields.Char('Sale notes',
                            size = 250,
                            help = 'Notes for sale (will be displayed as warning every time when selecting the party as customer)'
                            )
    dolibarr_pid = fields.Integer('Dolibarr party id',
                                  states = { 'invisible': True, },
                                  readonly = True,
                                  help = 'party id from dolibarr (for import purposes only)')
    dolibarr_cid = fields.Integer('Dolibarr contact id',
                                  states = { 'invisible': True, },
                                  readonly = True,
                                  help = 'contact id from dolibarr (for import purposes only)')
    # standard for invoice/LS:
    accept_exact_amounts = fields.Boolean('Exact quantities',
                                          help = 'Customer only accept exact quantities')
    charge_setup_costs = fields.Boolean('Setup costs',
                                        help = 'Customer gets charged setup costs seperately')
    # general stuff
    #place_of_jurisdiction = fields.Char('Place of jurisdiction', size=100)
    
    @classmethod
    def default_accept_exact_amounts(cls):
        return False

    @classmethod
    def default_charge_setup_costs(cls):
        return True
    
    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('dolibarrpid_uniq', Unique(t, t.dolibarr_pid), 'dolibarr_id_dolibarrpid_uniq'),
            ('dolibarrcid_uniq', Unique(t, t.dolibarr_cid), 'dolibarr_id_dolibarrcid_uniq'),
        ]

    @classmethod
    def copy(cls, parties, default=None):
        '''
        Allow copying of entries that have dolibarr_[pc]id by setting them to None
        as it is pointless to copy (and they are unique)
        '''
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('dolibarr_pid', None)
        default.setdefault('dolibarr_cid', None)
        return super().copy(parties, default=default)


class Replace(metaclass=PoolMeta):
    __name__ = 'party.replace'

    @classmethod
    def fields_to_replace(cls):
        return super().fields_to_replace() + [
            ('party.party-sale.sale', 'party'),
        ]
