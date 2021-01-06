#!/usr/bin/env python3.8

import sys
import codecs
import csv
from proteus import config, Model, Wizard, Report
pcfg = config.set_trytond(database='tryton', config_file='/etc/tryton/trytond.conf')

ENCODING = 'iso-8859-15'

DEBUG = True

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
SubD = Model.get('country.subdivision')
Cont = Model.get('party.contact_mechanism')
Ident = Model.get('party.identifier')
Prel = Model.get('party.relation.all') 
PrelTyp = Model.get('party.relation.type')

PREL_EMPLOYEE = 'Mitarbeiter'
PREL_EMPLOYER = 'Arbeitgeber'

lang_de, = Lang.find([('code', '=', 'de')]) # default language

def get_or_create_category(cname):
    try:
        cat, = Categ.find([('name', '=', cname)])
        # FIXME: assuming there will only be one with that name
        # when i think that it is possible to have the same name, but not top level
        return cat
    except:
        cat = Categ(name = cname)
        cat.save()
        return cat


country_at, = Country.find([('code', '=', 'AT')])

def add_note(res, text, e=None):
    # no error handling here cuz if this fails i want it to abort ..
    note = Note()
    note.resource = res
    note.message = text
    note.unread = True
    if e:
        note.message += f'\nException:\n{e}'
    note.save()

def party_complete_print(p):
    ret = f'''

############################
{p.code=}
{p.name=}
{p.legal_name=}
{p.salutation=}
{p.pn_name=}
{p.dolibarr_pid=}
{p.dolibarr_cid=}
{p.customer_no=}
{p.supplier_no=}'''
    if p.addresses:
        for ad in p.addresses:
            ret += f'''
Address:
  {ad.street=}
  {ad.city=}
  {ad.zip=}
'''
            if ad.subdivision:
                ret += f'  {ad.subdivision.name=}'
            if ad.country:
                ret += f'  {ad.country.name=}'
    if p.contact_mechanisms:
        for cm in p.contact_mechanisms:
            ret += f'''
Contact Mechanism:
  {cm.value=}
  {cm.type=}'''
    notes=Note.find([('resource', '=', p)])
    if notes:
        for n in notes:
            ret += f'''
Note:
#####
{note.message=}
#####
'''
    return ret + '''
############################

'''

def copy_address_data(from_, to):
    '''
    copies relevant (for this import) fields
    '''
    try:
        to.street = from_.street
        to.city = from_.city
        to.zip = from_.zip
        to.subdivision = from_.subdivision
        to.country = from_.country
        to.save()
    except:
        return False
    return True

    
#########################
# misc helper functions #
#########################
    
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

def print_progress(ncount):
    scount = ' '
    if ncount % 1000 == 0:
        scount = 'M'
    elif ncount % 500 == 0:
        scount = 'D'
    elif ncount % 100 == 0:
        scount = 'C'
    elif ncount % 50 == 0:
        scount = 'L'
    elif ncount % 10 == 0:
        scount = 'X'
    else:
        scount = '.'
    print(scount, end='', flush = True)


################
# Party import #
################

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

def party_import():
    party_fname='data/export_societe_1.csv' # colums above
    with codecs.open(party_fname, 'r', ENCODING) as fp:

        reader = csv.reader(fp)

        headers = next(reader)
        print(f'{headers=}')

        ncount = 0
        for row in reader:
            np = Party()
            np.name = row[1].strip()
            np.lang = lang_de # since row[20] is empty ..
            try:
                np.dolibarr_pid = int(row[0])
                np.save() # save here so we got basic stuff that shouldn't fail and can attach notes,..
            except Exception as e:
                print(f'\nError adding dolibar_pid {row[0]}.\n\n{e}')
                continue

            # try:
            #     exists = Party.find([('dolibarr_pid', '=', int(row[0]))])
            #     if not exists:
            #         # no need to check this needs to be present or the export is bogus
            #         np.dolibarr_pid = int(row[0])
            #     else:
            #         add_note(np, f'Dolibarr party ID <<{row[0]=}>> already exists !!')
            # except Exception as e:
            #     add_note(np, f'Error adding dolibarr_pid <<{row[0]=}>>', e)

            np.categories.append(get_or_create_category('Import 2020-01-05'))
            # Address
            addr = np.addresses[0] # seems like every contact comes witha t least one address
            if row[5] and row[5].strip():
                try:
                    addr.zip = row[5].strip()
                except Exception as e:
                    add_note(np, f'Error adding ZIP with <<{row[5]=}>>', e)
            if row[4] and row[4].strip():
                try:
                    addr.street = row[4].strip()
                except Exception as e:
                    add_note(np, f'Error adding street with <<{row[4]=}>>', e)                   
            if row[6] and row[6].strip():
                try:
                    addr.city = row[6].strip()
                except Exception as e:
                    add_note(np, f'Error adding city with <<{row[6]=}>>', e)                   

            if row[9] and row[9].strip():
                try:
                    addr.country, = Country.find([('code', '=', row[9].strip())])
                except Exception as e:
                    add_note(np, f'Error adding country with code <<{row[9]=}>>', e)
            # default country set later to avoid creating dummy addresses
            # with just the default country
            if row[7] and row[7].strip():
                try:
                    sd, = SubD.find([('name', '=', row[7].strip())])
                    addr.subdivision = sd
                except Exception as e:
                    add_note(np, f'Error adding country subdivision <<{row[7]=}>>', e)
            # address done .. save
            try:
                # check if we have *any* data
                if addr.city or addr.street or addr.country or addr.subdivision or addr.zip:
                    if not addr.country:
                        # if we have an address but no country we set the default
                        print(f'adding default country to address {np.code=} {np.name=} {addr.full_address=}')
                        addr.country = country_at
                    addr.save()
                else:
                    # tested in proteus that this removes it from the party
                    addr.delete() # remove address
            except Exception as e:
                add_note(np, 'Error saving address', e)

            # Contact Mechanisms
            # save after every one to make sure validation triggers
            if row[10] and row[10].strip():
                try:
                    cm = Cont(type='phone')
                    cm.value = row[10].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding phone number <<{row[10]=}>>', e)
            if row[11] and row[11].strip():
                try:
                    cm = Cont(type='fax')
                    cm.value = row[11].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding fax number <<{row[11]=}>>', e)
            if row[13] and row[13].strip():
                try:
                    cm = Cont(type='email')
                    cm.value = row[13].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding email <<{row[13]=}>>', e)
            if row[14] and row[14].strip():
                try:
                    cm = Cont(type='website')
                    cm.value = row[14].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding website <<{row[14]=}>>', e)

            # misc
            if row[2] and row[2].strip():
                try:
                    np.customer_no = row[2].strip()
                except Exception as e:
                    add_note(np, f'Error adding customer number <<{row[2]=}>>', e)
            # skipping row[3] Lieferanten-Code as tehre is no data in the whole DataSet
            iderr = False
            # save after every line for validation purposes
            if row[12] and row[12].strip():
                try:
                    euvat = Ident(type='eu_vat')
                    euvat.code = row[12].strip()
                    euvat.party = np # party is required to save
                    euvat.save()
                except Exception as e:
                    iderr = True
                    add_note(np, f'Error adding EU VAT <<{row[12]=}>>', e)
            if row[23] and row[23].strip():
                try:
                    atbus=Ident(type='at_businessid')
                    atbus.code= row[23].strip()
                    atbus.party = np # party is required to save
                    atbus.save()
                except Exception as e:
                    iderr = True
                    add_note(np, f'Error adding EU VAT <<{row[23]=}>>', e)
            if iderr:
                np.categories.append(get_or_create_category('ID Falsch'))
            # ignoring 25 (Rechtsform) and 17 (Typ des Partners)
            if row[26] and row[26].strip():
                try:
                    np.pn_name = row[26].strip()
                except Exception as e:
                    add_note(np, f'Error adding PN Name <<{row[26]=}>>', e)
            # notes from Dolibarr
            has_note = False
            if row[15] and row[15].strip() and strip_tags(row[15]).strip():
                add_note(np, 'Notiz (privat):\n\n' + strip_tags(row[15]).strip())
                has_note = True
            if row[16] and row[16].strip() and strip_tags(row[16]).strip():
                add_note(np, 'Notiz (öffentlich):\n\n' + strip_tags(row[16]).strip())
                has_note = True
            if has_note:
                np.categories.append(get_or_create_category('Notiz'))

            # save everything
            try:
                np.save()
            except Exception as e:
                add_note(np, 'Error saving party', e)
            ncount += 1
            print_progress(ncount)

all_parties=Party.find()
answer= input(f'Found {len(all_parties)} parties. Type "start" to start the party import (or "all" to run everything): ')
if answer == 'start' or answer == 'all':
    party_import()
    print('\nParty import done')
            
######################
# dolibarr contacts  #
######################

# CSV columns        
#  0 .. Kontakt-ID
#  1 .. Anrede
#  2 .. Nachname
#  3 .. Vorname
#  4 .. Position / Funktion
#  5 .. Privat
#  6 .. Adresse
#  7 .. PLZ
#  8 .. Stadt
#  9 .. Bundesland
# 10 .. Land # friggin french .. again
# 11 .. Ländercode
# 12 .. Telefon
# 13 .. Fax
# 14 .. Mobile
# 15 .. E-Mail
# 16 .. Unternehmen-ID <== match this to the parties
# 17 .. Firmenname # From company table
# 18 .. Weitere Email 
# 19 .. Handy 2
# 20 .. Akadem. Titel
# 21 .. Weiteres Telefon
# 22 .. Weiteres Telefon 2
# 23 .. PN NAME # from company table
# 24 .. Status # From Company table
# 25 .. Kundennummer # From Company Table
# 26 .. Lieferanten-Code # from company table

def contact_import():
    party2_fname='data/export_societe_2.csv' # columns above
    with codecs.open(party2_fname, 'r', ENCODING) as fp:
        reader = csv.reader(fp)

        headers = next(reader)
        print(f'{headers=}')

        ncount = 0
        for row in reader:
            # TODO: somehow check if there is any point in this being it's own party .. but
            # but difficult to automate
            np = Party()
            np.name = f'{row[2].strip()} {row[3].strip()}'.strip()
            if row[20] and row[20].strip():
                np.name += f', {row[20].strip()}'
            # make an educated guess based on 99% of the entries
            np.legal_name = f'{row[20].strip()} {row[3].strip()} {row[2].strip()}'.strip()
            np.lang = lang_de
            np.salutation = row[1].strip()
            try:
                np.dolibarr_cid = int(row[0])
                np.save()
            except Exception as e:
                print(f'\nError adding dolibarr_cid {row[0]}.\n\n{e}')
                continue
            np.categories.append(get_or_create_category('Import 2020-01-05'))

            # first add relation to (dolibarr) party
            try:
                prelt, = PrelTyp.find([('name', '=', PREL_EMPLOYEE)])
                pemp, = Party.find([('dolibarr_pid','=', int(row[16]))])
                nr = Prel(type = prelt)
                nr.from_ = np
                nr.to = pemp
                nr.save()
            except Exception as e:
                print(f'Error getting employee party relation type . aborting!\n{e}')
                return False

            # Address
            addr = np.addresses[0]
            if row[7] and row[7].strip():
                try:
                    addr.zip = row[7].strip()
                except Exception as e:
                    add_note(np, f'Error adding ZIP with <<{row[7]=}>>', e)
            if row[6] and row[6].strip():
                try:
                    addr.street = row[6].strip()
                except Exception as e:
                    add_note(np, f'Error adding street with <<{row[6]=}>>', e)                   
            if row[8] and row[8].strip():
                try:
                    addr.city = row[8].strip()
                except Exception as e:
                    add_note(np, f'Error adding city with <<{row[8]=}>>', e)                   

            if row[11] and row[11].strip():
                try:
                    addr.country, = Country.find([('code', '=', row[11].strip())])
                except Exception as e:
                    add_note(np, f'Error adding country with code <<{row[11]=}>>', e)
            # default country set later to avoid creating dummy addresses
            # with just the default country
            if row[9] and row[9].strip():
                try:
                    sd, = SubD.find([('name', '=', row[9].strip())])
                    addr.subdivision = sd
                except Exception as e:
                    add_note(np, f'Error adding country subdivision <<{row[9]=}>>', e)
            # address done .. save
            try:
                # check if we have *any* data
                if addr.city or addr.street or addr.country or addr.subdivision or addr.zip:
                    if not addr.country:
                        # if we have an address but no country we set the default
                        print(f'adding default country to address {np.code=} {np.name=} {addr.full_address=}')

                        addr.country = country_at
                    addr.save()
                else:
                    addr.delete() # remove address
            except Exception as e:
                add_note(np, 'Error saving address', e)

            # Contact Mechanisms
            # save after every one to make sure validation triggers
            if row[12] and row[12].strip():
                try:
                    cm = Cont(type='phone')
                    cm.value = row[12].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding phone number <<{row[12]=}>>', e)
            if row[21] and row[21].strip():
                try:
                    cm = Cont(type='phone')
                    cm.value = row[21].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding phone number <<{row[21]=}>>', e)
            if row[22] and row[22].strip():
                try:
                    cm = Cont(type='phone')
                    cm.value = row[22].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding phone number <<{row[22]=}>>', e)
            if row[14] and row[14].strip():
                try:
                    cm = Cont(type='mobile')
                    cm.value = row[14].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding phone number <<{row[14]=}>>', e)
            if row[19] and row[19].strip():
                try:
                    cm = Cont(type='mobile')
                    cm.value = row[19].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding phone number <<{row[19]=}>>', e)
            if row[13] and row[13].strip():
                try:
                    cm = Cont(type='fax')
                    cm.value = row[13].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding fax number <<{row[13]=}>>', e)
            if row[15] and row[15].strip():
                try:
                    cm = Cont(type='email')
                    cm.value = row[15].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding email <<{row[15]=}>>', e)
            if row[18] and row[18].strip():
                try:
                    cm = Cont(type='email')
                    cm.value = row[18].strip()
                    cm.party = np
                    cm.save()
                except Exception as e:
                    add_note(np, f'Error adding email <<{row[18]=}>>', e)

            np.save()
            ncount += 1
            print_progress(ncount)

all_parties=Party.find()
if answer != 'all':
    answer= input(f'Found {len(all_parties)} parties. Type "start" to start the contact import: ')
if answer == 'start' or answer == 'all':
    contact_import()
    print('\nContact import complete')

#########################
# Party/Contact cleanup #
#########################

# IMPORTANT: These functions *only* compare what is imported above. Run at a later stage
# at your own risk !

def compare_contact_mechanism_data(c1, c2, ignoreType = False):
    '''
    returns True if they are the same, False otherwise
    ignoreType = True just compares values
    '''
    if c1.value == c2.value:
        if ignoreType:
            return True
        else:
            if c1.type == c2.type:
                return True
    return False

def compare_address_data(a1, a2, acceptSubset=False, ignoreSubdivision=False):
    '''
    returns True if they are the same, False otherwise

    when acceptSubset is set consider them the same if a2 is a subset of a1 as well
    (does NOT consider them equal if a1 is a subset of a2 (would need to update a1
    in this case..)
    
    it is up to the caller to - if needed - also call this function with a1 and a2
    swapped .. and then deal with it
    '''
    if not acceptSubset:
        if a1.zip != a2.zip:
            return False
        if a1.street != a2.street:
            return False
        if a1.city != a2.city:
            return False
        if not ignoreSubdivision:
            if a1.subdivision and a2.subdivision and a1.subdivision.id != a2.subdivision.id:
                print('Subdivision differs')
                return False
        if a1.country and a2.country and a1.country.id != a2.country.id:
            return False
    else:
        if a2.zip and a1.zip != a2.zip:
            return False
        if a2.street and a1.street != a2.street:
            return False
        if a2.city and a1.city != a2.city:
            return False
        if not ignoreSubdivision:
            if a1.subdivision and a2.subdivision and a1.subdivision.id != a2.subdivision.id:
                print('Subdivision differs')
                return False
        if a2.country and a1.country.id != a2.country.id:
            return False
    return True

def party_cleanup():
    ppar = Party.find([('dolibarr_pid', '>', '-1')])
    prelt, = PrelTyp.find([('name', '=', PREL_EMPLOYER)])
    print(f'Employer relationship: {prelt.id=}, {prelt.name}')
    ndupcnt = 0
    for p in ppar:
        try:
            r, = p.relations
            # first a check nothing went .. weird .. in which case abbort
            if r.type.id != prelt.id:
                print(f'Something is not right with {p.name=} {p.code=}')
                return
            # assume p1 is always the dolibarr party and p2 is the contact
            # otherwise would have to maybe consider legal_name
            if r.from_.name != r.to.name:
                # name is already different. move on to the next one
                continue
            # purposely ignore fields only present in the dolibarr party by definition:
            # pn_name, identities, customer_no
            
            # Address
            # compare address (there is only one possible address from the import
            # so can ignore more
            a1 = r.from_.addresses[0] if r.from_.addresses else None
            a2 = r.to.addresses[0] if r.to.addresses else None

            if not compare_address_data(a1, a2, True, True):
                # not the same or a2 being a subset of a1
                if not compare_address_data(a2, a1, True, True):
                    # not matching either way eve if it is a subset the other way around
                    print(f'Addresses are different {r.from_.code} {r.to.code} .. adding 2nd address.. ')
                    #print(party_complete_print(r.from_))
                    #print(party_complete_print(r.to))
                    # no match .. let's just add a 2nd address
                    adn = r.from_.addresses.new()
                    copy_address_data(a2, adn) 
                else:
                    print(f'a1 is a subset of a2 {r.from_.code} {r.to.code} .. updating a1..')
                    #print(party_complete_print(r.from_))
                    #print(party_complete_print(r.to))
                    copy_address_data(a2, a1)
            # Addresses match, or a2 is a subset of a1 (in which case we ignore a2)
            r.from_.save() # save after checking and/or copying addrsss
            
            # Contact Mechanisms
            # if we got here .. merge the contact_mechanisms from a2 into a1, while
            # avoiding duplicates

            pcm = r.from_.contact_mechanisms
            ccm = r.to.contact_mechanisms

            if ccm:
                # get a quick to search list of original contact_mechanisms
                pcm_orig = []
                if pcm:
                    for cm in pcm:
                        pcm_orig.append(f'{cm.type} {cm.value_compact}')
                for cm in ccm:
                    if f'{cm.type} {cm.value_compact}' not in pcm_orig:
                        r.from_.contact_mechanisms.new(type = cm.type, value = cm.value)
                    else:
                        #print(f'skipping duplicate {r.from_.code=} {cm.type=} {cm.value=}')
                        pass
                r.from_.save() # save after adding contact mechanisms
                        
            # Notes

            cnotes = Note.find([('resource', '=', r.to)])
            if cnotes:
                for cn in cnotes:
                    add_note(r.from_, f'NOTE from contact {r.to.dolibarr_cid=}:\n\n {cn.message}')
            # notes are saved in add_note so no need to save here
            # delete the unneeded party
            print('Deleting party:\n')
            print(party_complete_print(r.to))
            r.to.delete()
            ndupcnt += 1

        except:
            # No interest in any parties without relation
            # (there should be none, but to be sure..
            # also not interested in parties with more than one relation as those
            # cannot be merged automatically in any case
            pass
    print(f'{ndupcnt} duplicates found. Data merged if needed and duplicates deleted')
                

if answer != 'all':
    answer = input('Do you want to run the party cleanup? Type "start" to start cleanup: ')
if answer == 'start' or answer == 'all':
    party_cleanup()
    print('\nParty cleanup done')
#
print('Import complete')
        
