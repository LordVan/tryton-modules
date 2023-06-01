from trytond.protocols.wrappers import (
    HTTPStatus, Response, abort, with_pool, with_transaction)
from trytond.pool import Pool
from trytond.wsgi import app

def create_carddav():
    pool = Pool()
    Party = pool.get('party.party')
    ret = ''
    for p in Party.search([]):
        ret += p.to_vcard()
    return ret

@app.route('/<database_name>/party/carddav', methods = {'GET'})
@with_pool
@with_transaction()
def vcards(request, pool):
    return Response(create_carddav(), content_type='text/vcard')
