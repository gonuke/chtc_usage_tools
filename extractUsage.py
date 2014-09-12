#!/usr/bin/env python

import sqlite3
import argparse
import datetime
import chtc_usage_tools as cut
import matplotlib.pyplot as plt
import matplotlib.dates as mpld
import matplotlib as mpl

mpl.rcParams['axes.color_cycle'] = ['r', 'k', 'c']

conn = cut.usage_db_connect()
curs = conn.cursor()

parser = argparse.ArgumentParser(description='A tool to extract usage data')
parser.add_argument('--project',help='The name of a project over which to summarize the results',nargs="*",type=lambda s: unicode(s,'utf8'))
parser.add_argument('--pool',help='Limit the data to a single pool',nargs="*")
parser.add_argument('-s','--sum',help="Sum across pools",action='store_true')

args=parser.parse_args()

### projects
usage_projects=set(cut.get_db_projects(curs))
if args.project:
    usage_projects=set(args.project).intersection(usage_projects)

### pools
usage_pools=cut.get_db_pools(curs)
if args.pool:
    usage_pools=set(args.pool).intersection(usage_pools)

# sum over all users for each pool
sum_usage_pools = map(lambda x: "sum(" + x + ")", usage_pools)
col_query = ','.join(sum_usage_pools)

# sum over all pools
if args.sum:
    col_query  += ',(' + '+'.join(sum_usage_pools) + ')'

project_data = {}

for project in usage_projects:
    print project
    curs.execute('select enddate,' + col_query + ' from usage where userid in (select rowid from users where project=?) group by enddate', (project,))
    project_data[project] = {'dates':[], 'usage':[]}

    rows = curs.fetchall()

    for row in rows:
        project_data[project]['dates'].append(datetime.datetime.strptime(row[0],'%Y-%m-%d'))
        project_data[project]['usage'].append(row[1:])
    if (max(project_data[project]['usage']) > 0):
        plt.plot_date(mpld.date2num(project_data[project]['dates']),map(lambda x: x[-1], project_data[project]['usage']),'-',xdate=True,label=project)

#print project_data
plt.legend(loc='upper left')
plt.ylabel('cpu-hours per day')
plt.show()
