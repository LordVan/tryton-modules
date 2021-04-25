import sys
import codecs
import csv
import re

from datetime import datetime

from io import StringIO
from html.parser import HTMLParser

# copied from dolibarr_csv_import as that is not suitable to import

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()
    
def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def add_note(res, text, e=None):
    # no error handling here cuz if this fails i want it to abort ..
    Note = pool.get('ir.note')
    note = Note()
    note.resource = res
    note.message = text
    note.unread = True
    if e:
        note.message += f'\nException:\n{e}'
    note.save()

LOG_STDOUT = True
flog = None
if not LOG_STDOUT:
    flog = open('dolibarr_project_import.log', 'w+')
    
def log(message, print_anyway = False):
    if LOG_STDOUT:
        print(message)
    else:
        flog.write(message + '\n')
        flog.flush()
        if print_anyway:
            print(message)

################################
# end generic helper functions #
################################
            
###################
# SQL from export #
###################

# \copy (
#     SELECT
#     p.rowid AS proj_id, TRIM(p.ref) AS number,
#     p.dateo AS start_date, pe.date_start_extra,p.datee AS end_date, pe.date_end_extra,
#     TRIM(REPLACE(p.title,'Bestellung', '')) AS cust_ref, TRIM(pe.commission) AS commission,
#     TRIM(p.description) AS description, p.date_close, TRIM(REGEXP_REPLACE(REGEXP_REPLACE(p.note_public, E'<[^>]+>', '', 'gi'), E'[\\n\\r]+', ' ', 'gi')) AS note,
#     soc.rowid AS customer_id, soc.nom AS customer_name
#     FROM llx_projet p
#     INNER JOIN llx_societe soc ON soc.rowid = p.fk_soc
#     INNER JOIN llx_projet_extrafields pe ON pe.fk_object = p.rowid
#     ORDER BY p.rowid DESC
#     ) TO 'dolibarr_projects_2021-04-25.csv' WITH csv HEADER;

# \copy (
#     SELECT
#     p.rowid AS proj_id, TRIM(p.ref) AS number,
#     sp.rowid AS contact_id, CONCAT_WS(' ', sp.lastname, sp.firstname) AS contact_name
#     FROM llx_projet p
#     INNER JOIN llx_element_contact ec on ec.element_id = p.rowid
#     INNER JOIN llx_socpeople sp on SP.rowid = ec.fk_socpeople
#     ORDER BY p.rowid DESC
#     ) TO 'dolibarr_projects_contacts_2021-04-25.csv' WITH csv HEADER;

# ignoring if the 2 potential extra digits for month are valid or not to simplify regex
pat_num = re.compile('^(\d{4})\d{0,2}/(\d{4})$')

def fix_number(num):
    'fix the issue with dolibarr where it needed months appended to the year'
    return '/'.join(pat_num.match(num).groups())
    #

def import_projects(pool, transaction):
    Party = pool.get('party.party')
    Comp = pool.get('company.company')
    Sale = pool.get('sale.sale')
    #Date = pool.get('ir.date')

    c, = Comp.search([('id', '=', '1')]) # I know it is always this so making "an assumption"
    
    with codecs.open('dolibarr_projects_2021-04-25.csv', 'r', 'utf-8') as fp:
        reader = csv.reader(fp)

        headers = next(reader)
        log(f'{headers}')

        #       0,     1,         2,               3,       4,             5,       6,         7,          8,         9,  10,         11,           12
        # proj_id,number,start_date,date_start_extra,end_date,date_end_extra,cust_ref,commission,description,date_close,note,customer_id,customer_name
        
        ncount = 0

        for row in reader:
            try:
                s = Sale()
                # things that are the same for all imported sales:
                s.company = c
                s.currency = c.currency
                s.shipment_method = 'manual'
                s.invoice_method = 'manual'
                
                s_comment = '' # comment field used for notes, description and date_closed from dolibarr
                s.dolibarr_pid = int(row[0]) # for contact matching later
                s.number = fix_number(row[1])
                s.sale_date = datetime.strptime(row[2], '%Y-%m-%d').date()
                if row[3]:
                    s.sale_date_extra = row[3]
                if row[4]:
                    s.shipping_date = datetime.strptime(row[4], '%Y-%m-%d').date()
                if row[5]:
                    s.shipping_date_extra = row[5]
                if row[6]:
                    s.reference = row[6]
                if row[7]:
                    s.description = row[7]
                # no need for .strip() as the SQL output was trimmed already
                if row[8]:
                    s_comment += f'description: {row[8]}\n'
                if row[9]:
                    # use this to determine if confiremd or done
                    s_comment += f'date_close: {row[9]}\n'
                    s.state = 'done'
                else:
                    s.state = 'confirmed'
                if row[10]:
                    s_comment += f'note: {row[10]}\n'
                s.comment = s_comment.strip() # get rid of extra linebreak here is easier
                p, = Party.search([('dolibarr_pid', '=', row[11])]) 
                s.party = p
                # just use the first one here as it is not too important with the historical data
                s.shipment_address = p.addresses[0]
                s.invoice_address = p.addresses[0]
                s.save()
            except Exception as e:
                log(f'\nError adding project {row[1]}.\n\n{e}')

def import_project_contacts(pool, transaction):
    Sale = pool.get('sale.sale')
    Party = pool.get('party.party')

    #with codecs.open('dolibarr
    
# if __name__ == '__main__':
#     print('''Do not run this directly. This is to be imported and called from trytond_console,
# since when using proteus we cannot ignore automatic sequences,...''')
#     sys.exit(1)
