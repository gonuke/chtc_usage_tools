#!/usr/bin/env python

import argparse
import mailbox
import urlparse
import datetime
import sqlite3
import lxml.html

import chtc_usage_tools as cut

def check_usage_tables(curs):
    '''Create the necessary DB tables if they don't already exist'''
    curs.execute('CREATE TABLE IF NOT EXISTS users ( username varchar(255), project varchar(255))')
    curs.execute('CREATE TABLE IF NOT EXISTS usage ( userid int, enddate datetime)')

def get_html_from_url(url):
    return lxml.html.parse(url)

def get_html_from_msg(msg):
    return lxml.html.fromstring(msg)

def get_table(html_tree,table_id):
    # get the first element with id=table_id from anywhere in the doctree
    # assumes only one and that it's a table
    table = html_tree.xpath('//*[@id="' + table_id + '"]/tbody')
    if len(table) == 0:
        table = html_tree.xpath('//*[@id="' + table_id + '"]')
    return table[0]

def parse_date(date_string):
    date = map(int,date_string.split('-'))
    return datetime.date(date[0],date[1],date[2])

def parse_headers(header_rows):

    # first row contains start date and names of pools
    cells = header_rows[0].getchildren()
    if cells[1].text_content() == '':
        return '','',[]
    from_date = parse_date(cells[1].text_content().strip())

    # get list of compute pools
    pools = []
    for cell in cells[2:]:
        pool_name = cell.text_content().strip().lower()
        pools.append(pool_name)

    # second row contains end date
    cells = header_rows[1].getchildren()
    to_date = parse_date(cells[1].text_content().strip())

    return from_date, to_date, pools

def extract_usage_data(source,source_type):
    """Get all the usage data from the table with id='chtc_usage_by_user' from url"""

    if source_type == 'html_file':
        html_tree = lxml.html.parse(source)
    elif source_type == 'mbox':
        msg_html = source.get_payload()[0].as_string()
        # eliminate rogue strings that prevent HTML parsing
        msg_html = msg_html.replace("!\r\n ","")
        html_start = msg_html.find('<html>')
        html_tree = lxml.html.fromstring(msg_html[html_start:])

    rows = get_table(html_tree,'chtc_usage_by_user')
    
    from_date,to_date,pools = parse_headers(rows[0:3])

    # complex logic to find column with project name
    # This is kind of messy
    project_idx = pools.index("project")
    if project_idx == 0:
        project_idx = 2
    elif project_idx == len(pools)-1:
        project_idx = (len(pools)-1)*2+2
    else:
        print "error"

    if from_date == '':
        return '',[]

    alldata = []
    
    for row in rows[3:]:
        datarow = {}
        cells = row.getchildren()
        datarow['user'] = cells[1].text_content().strip()
        datarow['group'] = cells[project_idx].text_content().strip()
        datarow['usage'] = {}
        cell_idx = 2
        for pool in pools:
            if pool == "project":
                cell_idx += 1
                continue

            if pool != "total":
                datarow['usage'][pool] = int(''.join(cells[cell_idx].text_content().strip().split(',')))
            cell_idx += 2
    
        alldata.append(datarow)
    
    return to_date,alldata

def date_exists(curs,date):
    curs.execute('SELECT * FROM usage WHERE enddate=?',(date,))
    return curs.fetchone()

def get_all_usage_data(sourceURI):
    
    remote_html_schemes = ['http','ftp']

    usage_data = {}
    source = urlparse.urlparse(sourceURI)

    if source.scheme == 'mbox':
        print "Adding usage data from mbox file " + source.path
        for msg in mailbox.mbox(source.path):
            date, alldata = extract_usage_data(msg,source.scheme)
            if date != '':
                usage_data[date] = alldata
    elif source.scheme == 'file':
        print "Adding usage data from local HTML file " + source.path
        date,alldata = extract_usage_data(source.path,'html_file')
        usage_data[date] = alldata
    elif source.scheme in remote_html_schemes:
        print "Adding usage data from remote HTML file " + sourceURI
        date,alldata = extract_usage_data(sourceURI,'html_file')
        usage_data[date] = alldata
    else:
        print "Source scheme " + source.scheme + " is not currently supported."
    return usage_data

def get_db_pools(curs):
    """get list of columns already in usage table"""
    cursor = curs.execute('select * from usage')
    return map(lambda x: x[0], cursor.description)

def update_db_pools(curs,alldata):
    '''get all compute pools already in db'''
    db_pools = get_db_pools(curs)
        
    # search for pools in db and add missing ones
    for pool in alldata[0]['usage'].keys():
        if pool not in db_pools:
            print "\tAdding new pool: " + pool
            curs.execute('ALTER TABLE usage ADD COLUMN ' + pool + ' int DEFAULT 0')
    conn.commit()

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

parser = argparse.ArgumentParser(description='A tool to place data into the usage db')
parser.add_argument('source',help='A URI to a source of data.  Must be one of html,ftp,file ' +
                    'for a simple HTML file, or mbox for a mailbox of usage emails.')
parser.add_argument('database',help='An sqlite3 database file',default='chtc_usage.db')

args = parser.parse_args()

# get all data
usage_data = get_all_usage_data(args.source)

conn = sqlite3.connect(args.database)
curs = conn.cursor()

check_usage_tables(curs)

for date,alldata in usage_data.iteritems():

    # check for data on this date already and don't add again
    if date_exists(curs,date):
        print("This date " + str(date) + " has already been added.")
        continue

    print("Adding date " + str(date) + " has been added.")
        
    update_db_pools(curs,alldata)

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
        


        


