from trytond.model import fields, Unique
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool

__all__ = ['Party']


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
    legal_name = fields.Char('Legal name',
                             help = 'Legally correct name')
    salutation = fields.Char('Salutation',
                             size = 50) # limiting length since more seems useless
    dolibarr_pid = fields.Integer('Dolibarr party id',
#                                  readonly = True,
                                  help = 'party id from dolibarr (for import purposes only)')
    dolibarr_cid = fields.Integer('Dolibarr contact id',
#                                 readonly = True,
                                 help = 'contact id from dolibarr (for import purposes only)')
    # general stuff
    #place_of_jurisdiction = fields.Char('Place of jurisdiction', size=100)
    

    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('dolibarrpid_uniq', Unique(t, t.dolibarr_pid), 'dolibarr_id_dolibarrpid_uniq'),
            ('dolibarrcid_uniq', Unique(t, t.dolibarr_cid), 'dolibarr_id_dolibarrcid_uniq'),
        ]
