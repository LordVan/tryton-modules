# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from . import product


def register():
    Pool.register(
#        product.Template,
        product.ProductMaterial,
        product.ProductMaterialSurface,
        product.Product,
        module='product_metal', type_='model')
