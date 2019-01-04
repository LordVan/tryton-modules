from trytond.model import fields
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool

#__all__= ['Template', 'Product']
__all__ = ['Product']


#class Template(metaclass=PoolMeta):
#    __name__ = 'product.template'


    
class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    material_thickness = fields.Float('Thickness (in mm)',
                                      digits=(5, 2))
    folder = fields.Text('Folder', size=3)

