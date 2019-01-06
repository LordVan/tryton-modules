from trytond.model import fields, ModelView, ModelSQL
from trytond.pyson import Eval, Bool, Id
from trytond.pool import PoolMeta, Pool

#__all__= ['Template', 'Product']
__all__ = ['Product', 'ProductMaterial', 'ProductMaterialSurface']


#class Template(metaclass=PoolMeta):
#    __name__ = 'product.template'

class ProductMaterial(ModelSQL, ModelView):
    'Material'

    __name__ = 'product.material'

    name = fields.Char('Name', required=True, size=50)


class ProductMaterialSurface(ModelSQL, ModelView):
    'Material surface'

    __name__ = 'product.material_surface'

    name = fields.Char('Name', required=True, size=50)


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    # project related
    folder = fields.Text('Folder', size=3)
    proj_1 = fields.Char('Project text line 1')
    proj_2 = fields.Char('Project text line 2')
    proj_3 = fields.Char('Project text line 3')
    proj_4 = fields.Char('Project text line 4')

    # material / production related
    material = fields.Many2One('product.material', 'Material')
    material_surface = fields.Many2One('product.material_surface', 'Material surface')
    material_thickness = fields.Float('Thickness (in mm)', digits=(5, 2))
    production_notes = fields.Text('Production notes')
    lvd_prog = fields.Char('LVD program', size=100)

    
