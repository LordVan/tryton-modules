from trytond.model import fields
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool

__all__ = ['Party']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'
    
    # custom stuff for us
    # unique could be added by adding sql constraints - see __setup__ in party module party.py
    customer_no = fields.Char('Customer number', size=9)
    supplier_no = fields.Char('Supplier number', size=9)
    pn_name = fields.Char('PN name', size=50)

    internal_name = fields.Char('Internal name', help='Name in the format for internal use')
    dolibarr_id = fields.Integer('Dolibarr id', help='id from dolibarr for import purposes only')
    # general stuff
    #place_of_jurisdiction = fields.Char('Place of jurisdiction', size=100)
    
