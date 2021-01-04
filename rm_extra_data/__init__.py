from trytond.pool import Pool
from . import party


def register():
    Pool.register(
        party.Party,
        module='rm_extra_data', type_='model')
    
