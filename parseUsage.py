#!/usr/bin/env python

import datetime
import sqlite3
import lxml.html

def get_table(url,table_id):
    # get the first element with id=table_id from anywhere in the doctree
    # assumes only one and that it's a table
    return lxml.html.parse(url).xpath('//*[@id="' + table_id + '"]')[0]

def parse_date(date_string):
    date = map(int,date_string.split('-'))
    return datetime.date(date[0],date[1],date[2])

def parse_headers(header_rows):
    # first row contains start date and names of pools
    cells = header_rows[0].getchildren()
    from_date = parse_date(cells[1].text_content().strip())

    # get list of compute pools
    pools = []
    for cell in cells[2:-2]:
        pools.append(cell.text_content().strip().lower())

    # second row contains end date
    cells = header_rows[1].getchildren()
    to_date = parse_date(cells[1].text_content().strip())

    return from_date, to_date, pools

def get_usage_data(url):
    """Get all the usage data from the table with id='chtc_usage_by_user' from url"""
    table = get_table(url,'chtc_usage_by_user')
    rows = table.getchildren()  
    
    from_date,to_date,pools = parse_headers(rows[0:3])
    
    alldata = []
    
    for row in rows[3:]:
        datarow = {}
        cells = row.getchildren()
        datarow['user'] = cells[1].text_content().strip()
        datarow['group'] = cells[-1].text_content().strip()
        datarow['usage'] = {}
        for pool, cell in zip(pools,cells[2:-4:2]):  # skip percent data - we can recalculate
            datarow['usage'][pool] = int(''.join(cell.text_content().strip().split(',')))
        alldata.append(datarow)
    
    return to_date,alldata


def get_db_pools(curs):
    """get list of columns already in usage table"""
    cursor = curs.execute('select * from usage')
    return map(lambda x: x[0], cursor.description)

def find_or_add_user(conn,user,group):
    """Search for a user in the user list.  If not found, add the user.  Return the user id."""
    curs = conn.cursor()
    curs.execute('SELECT rowid, username FROM users WHERE username=?', (user,) )
    firstrow = curs.fetchone()
    # if there is no entry, insert it, commit it and search for it again to get the id
    if not firstrow:
        curs.execute('INSERT INTO users VALUES (?,?)' , (user,group))
        conn.commit()
        curs.execute('SELECT rowid, username FROM users WHERE username=?' , (user,))
        firstrow = curs.fetchone()

    return firstrow[0]


# get all data
date,alldata = get_usage_data('http://monitor.chtc.wisc.edu/uw_condor_usage/usage1.shtml')

conn = sqlite3.connect('chtc_usage.db')
curs = conn.cursor()

# check for data on this date already and don't add again
curs.execute('SELECT * FROM usage WHERE enddate=?',(date,))
if curs.fetchone():
    print("This date " + str(date) + " has already been added.")
    quit()

# get all compute pools already in db    
db_pools = get_db_pools(curs)

# search for pools in db and add missing ones
for pool in alldata[0]['usage'].keys():
    if pool not in db_pools:
        curs.execute('ALTER TABLE usage ADD COLUMN ' + pool + ' int')
conn.commit()

# add each usage row
for row in alldata:
    # get user id
    user_id = find_or_add_user(conn,row['user'],row['group'])
    insert_cmd = 'INSERT INTO usage (userid, enddate,' + ','.join(row['usage'].keys()) + ') VALUES ('
    insert_cmd += ','.join(['?']*(len(row['usage'].keys())+2)) + ')'
    insert_data = [user_id,date]
    insert_data.extend(row['usage'].values())
    curs.execute(insert_cmd,tuple(insert_data))
    
conn.commit()
        


        


