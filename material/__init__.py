from trytond.pool import Pool
from . import material

def register():
    Pool.register(
        material.Material,
        module='material', type_='model')
    
    
