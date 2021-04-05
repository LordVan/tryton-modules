#!/usr/bin/env python3.8

# not an import from Dolibarr but from my custom system but still putting it here cuz it is easier

import sys
import codecs
import csv
from proteus import config, Model, Wizard, Report
pcfg = config.set_trytond(database='tryton', config_file='/etc/tryton/trytond.conf')

#ENCODING = 'iso-8859-15'
ENCODING ='utf-8'

DEBUG = True
LOG_STDOUT = True

#########################
# misc helper functions #
#########################

flog = None
if not LOG_STDOUT:
    flog = open('blv_import.log', 'w')
    
def log(message, print_anyway = False):
    if LOG_STDOUT:
        print(message)
    else:
        flog.write(message + '\n')
        flog.flush()
        if print_anyway:
            print(message)


# from BLV 2021-04-05
#to keep it simple just discard nonsensical combinations later
# all thicknesses

# uncommon ones removed from list will be added manually:
# select distinct  s.thickness, mat.name from blv_sheet s inner join blv_material mat on s.material_id =mat.id where thickness=2.99 or thickness=1.49
# ;
#  thickness |       name
#  -----------+------------------
#        1.49 | 1.4301 gebürstet
#        2.99 | DC 01
             
thicknesses = [0.20,
               0.25,
               0.30,
               0.40,
               0.50,
               0.60,
               0.70,
               0.75,
               0.80,
               1.00,
               1.20,
               1.25,
#               1.49,
               1.50,
               2.00,
               2.50,
#               2.99,
               3.00,
               4.00,
               5.00,
               6.00,
               8.00,
               10.00,
               12.00,
               15.00,
               20.00,
]

def import_sheetmetal_products():
    # assumes you got a Product Template called "Blechteil"
    # which will be the template for all of these
    Prod = Model.get('product.product')
    ProdTpl = Model.get('product.template')

    ptBlech = ProdTpl.find([('name', '=', 'Blechteil')])[0]

    #data from SQL DB BLV:
    #     SELECT mat.name, min(s.thickness), max(s.thickness) FROM blv_sheet AS s INNER JOIN blv_material mat ON s.material_id = mat.id WHERE mat.parent_id NOT IN (9,10,114) AND mat.name NOT LIKE 'Tischpl%'AND mat.name NOT LIKE 'Hartf%' AND mat.name NOT LIKE 'PE Pl%' AND mat.name NOT LIKE 'Pert%'  GROUP BY mat.name ORDER BY mat.name ;
    # with manual adjustments to outputbased on personal knowledge
    
    data_fname = 'blv_2021_04_05_minmax_mat.csv'
    with codecs.open(data_fname, 'r', ENCODING) as fp:
        reader = csv.reader(fp)

        headers = next(reader)
        log(f'{headers}')
        for row in reader:
            for thick in thicknesses:
                if thick >= float(row[1]) and thick <= float(row[2]):
                    #ignore thicknesses outside min, max for values
                    matnam = row[0].strip() + f' - {thick:.2f} mm'.replace('.',',')
                    log(matnam)
                    np = Prod()
                    np.suffix_code = matnam
                    np.material = row[0].strip()
                    np.sheet_thickness = thick
                    np.template = ptBlech
                    try: 
                        np.save()
                    except Exception as e:
                        log(f'Error saving {matnam} {thick}: {e}')
                        
                        
if __name__ == '__main__':
    import_sheetmetal_products()
