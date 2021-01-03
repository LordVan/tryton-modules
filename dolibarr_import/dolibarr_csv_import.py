#!/usr/bin/env python3.8

import sys
import codecs
import csv
from proteus import config, Model, Wizard, Report
pcfg = config.set_trytond(database='tryton', config_file='/etc/tryton/trytond.conf')

ENCODING = 'iso-8859-15'

#################
# Generic stuff #
#################

Party = Model.get('party.party')
Addr = Model.get('party.address')
Cont = Model.get('party.contact_mechanism')
Note = Model.get('ir.note')
Lang = Model.get('ir.lang')
Categ = Model.get('party.category')
Country = Model.get('country.country')
Cont = Model.get('party.contact_mechanism')

lang_de, = Lang.find([('code', '=', 'de')]) # default language
categ = Category()
categ.name = 'Import 2020-01-03' # TODO don't hardcode this but for now .. whatever
categ.save()
country_at, = Country.find([('code', '=', 'AT')])

def add_note(res, text, e=None):
    # no error handling here cuz if this fails i want it to abort ..
    note = Note()
    note.resource = res
    note.message = text
    if e:
        ner.message += f'\nException:\n[e]'
    note.save()


from io import StringIO
from html.parser import HTMLParser

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

################
# Party import #
################

party_fname='data/export_societe_1.csv' # this are companies/ individuals .. actual contact details for individual employees are in another file ..

# columns:
#  0 .. Id
#  1 .. Name
#  2 .. Kundennummer
#  3 .. Lieferanten-Code ## none available in data!!
#  4 .. Adresse
#  5 .. PLZ
#  6 .. Stadt
#  7 .. Bundesland
#  8 .. Land ## not using that it's in french (and code is more useful anyway)
#  9 .. Ländercode
# 10 .. Telefon
# 11 .. Fax
# 12 .. USt-IdNr.
# 13 .. E-Mail
# 14 .. Url
# 15 .. Anmerkung (privat)
# 16 .. Anmerkung (öffentlich)
# 17 .. Typ des Partners
# 18 .. Professional ID 6 # UNUSED (finanzamtnummer?)
# 19 .. Professional ID 5 # UNUSED
# 20 .. Standard-Sprache  # UNUSED
# 21 .. Professional ID 1 # UNUSED
# 22 .. Professional ID 2 # UNUSED
# 23 .. Professional ID 3 # at_businessid
# 24 .. Professional ID 4 # DVR .. irrelevant
# 25 .. Rechtsform # not needed for the moment and hardly and data in dump
# 26 .. PN NAME

all_parties=Party.find()
# for p in all_parties:
#     print(p.name)
#     print(p.addresses[0].full_address
#     )
print(f'Found {len(all_parties)} parties. If you still want to import press Enter otherwise abort')
sys.stdin.readline()

with codecs.open(party_fname, 'r', ENCODING) as fp:
    reader = csv.reader(fp)

    headers = next(reader)
    print(f'{headers=}')

    # TODO: check dolibarr_id (which is not added yet) if it exists..

    for row in reader:
        np = Party()
        #np.dolibarr_id = row[0]
        np.name = row[1]
        np.lang = lang_de
        np.categories.append(categ)
        np.save() # save here so we got basic stuff that shouldn't fail and can attach notes,..
        # Address
        addr = np.addresses.new()
        if row[5] and row[5].strip():
            addr.zip = row[5].strip()
        if row[4] and row[4].strip():
            addr.street = row[4].strip():
        if row[6] and row[6].strip():
            addr.city = row[6].strip()
        if row[9] and row[9].strip():
            try:
                addr.country, = Country.find([('code', '=', row[9].strip())])
            except Exception as e:
                add_note(np, f'Error adding country with code <<{row[9]}>>', e)
        else:
            addr.country = country_at
        addr.save()

        # Contact Mechanisms
        if row[10] and row[10].strip():
            try:
                cm = prm.contact_mechanisms.new(type='phone')
            except Exception as e:
                add_note(np, f'Error adding phone number <<{row[10]}>>', e)
        if row[11] and row[110].strip():
            try:
                cm = prm.contact_mechanisms.new(type='fax')
            except Exception as e:
                add_note(np, f'Error adding fax number <<{row[11]}>>', e)
        if row[13] and row[13].strip():
            try:
                cm = prm.contact_mechanisms.new(type='email')
            except Exception as e:
                add_note(np, f'Error adding email <<{row[14]}>>', e)
        if row[14] and row[14].strip():
            try:
                cm = prm.contact_mechanisms.new(type='website')
            except Exception as e:
                add_note(np, f'Error adding website <<{row[14]}>>', e)

        # misc
        if row[2] and row[2].strip():
            try:
                np.customer_no = row[2].strip()
            except Exception as e:
                add_note(np, f'Error adding customer number <<{row[2]}>>', e)
        # skipping row[3] Lieferanten-Code as tehre is no data in the whole DataSet
        if row[12] and row[12].strip():
            try:
                euvat=prm.identifiers.new(type='eu_vat')
                euvat.code= row[12].strip()
            except Exception as e:
                add_note(np, f'Error adding EU VAT <<{row[12]}>>', e)
        if row[23] and row[23].strip():
            try:
                atbus=prm.identifiers.new(type='at_businessid')
                atbus.code= row[23].strip()
            except Exception as e:
                add_note(np, f'Error adding EU VAT <<{row[23]}>>', e)
        # ignoring 25 (Rechtsform) and 17 (Typ des Partners)
        if row[26] and row[26].strip():
            try:
                prm.pn_name = row[26].strip()
            except Exception ad 3:
                add_note(np, f'Error adding PN Name <<{row[26]}>>', e)
        # notes from Dolibarr
        if row[15] and row[15].strip() and strip_tags(row[15]).strip():
            add_note(np, 'Notiz (privat):\n\n' + strip_tags(row[15]).strip())
        if row[165] and row[16].strip() and strip_tags(row[16]).strip():
            add_note(np, 'Notiz (öffentlich):\n\n' + strip_tags(row[16]).strip())

        # save everything
        np.save()
        
        
