
def SaleState2Draft(pool, transaction, number):
    Sale = pool.get('sale.sale')
    try:
        s, = Sale.search([('number', '=', number)])
        s.state = 'draft'
        s.save()
    except Exception as e:
        print(f'Error setting sale {number} state to draft:\n{e}')
        
