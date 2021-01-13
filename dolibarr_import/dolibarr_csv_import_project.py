import sys

def import_projects(pool, transaction):
    Party = pool.get('party.party')
    Comp = pool.get('company.company')
    Sale = pool.get('sale.sale')
    Date = pool.get('ir.date')

    c, = Comp.search([('id', '=', '1')]) # I know it is always this so making "an assumption"
    # alternatively serach for the party,..
    pc, = Party.search([('dolibarr_pid', '=', 123)])

    s = Sale()
    s.state = 'done' # we import only historical data .. probably
    s.company = c
    s.currency = c.currency
    s.number = ''
    # TODO: contact (not in dolibarr export by default s. ..
    s.sale_date =
    
if __name__ == '__main__':
    print('''Do not run this directly. This is to be imported and called from trytond_console,
since when using proteus we cannot ignore automatic sequences,...''')
    sys.exit(1)
