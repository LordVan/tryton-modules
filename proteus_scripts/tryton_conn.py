import myinit

from proteus import config, Model, Wizard, Report
pcfg = config.set_trytond(database='tryton', config_file='/etc/tryton/trytond.conf')
Party = Model.get('party.party')
Addr = Model.get('party.address')
Cont = Model.get('party.contact_mechanism')
Note = Model.get('ir.note')
Lang = Model.get('ir.lang')
Categ = Model.get('party.category')
Country = Model.get('country.country')
SubD = Model.get('country.subdivision')
Cont = Model.get('party.contact_mechanism')
Ident = Model.get('party.identifier')
Prel = Model.get('party.relation.all')
PrelTyp = Model.get('party.relation.type')
Prod = Model.get('product.product')
ProdTpl = Model.get('product.template')
Sale = Model.get('sale.sale')

try:
    prm, = Party.find([('code', '=', '1')])
except:
    print('Could not load party with code 1')
    
