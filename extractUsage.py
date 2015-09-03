#!/usr/bin/env python

import sqlite3
import argparse
import datetime
import chtc_usage_tools as cut
import matplotlib.pyplot as plt
import matplotlib.dates as mpld
import matplotlib as mpl
from numpy import array

mpl.rcParams['axes.color_cycle'] = ['r', 'k', 'c']

parser = argparse.ArgumentParser(description='A tool to extract usage data')
parser.add_argument('--project',help='The name of a project over which to summarize the results',nargs="*",type=lambda s: unicode(s,'utf8'))
parser.add_argument('--pool',help='Limit the data to a single pool',nargs="*")
parser.add_argument('-s','--sum',help="Sum across pools",action='store_true')
parser.add_argument('--span',choices=['day','month','year'],help="Time span across which to sum data",default='month')
parser.add_argument('database',help='The name of a database file')

args=parser.parse_args()

conn = cut.usage_db_connect(args.database)
curs = conn.cursor()

### projects
usage_projects=set(cut.get_db_projects(curs))
if args.project:
    usage_projects=set(args.project).intersection(usage_projects)

### pools
usage_pools=cut.get_db_pools(curs)
if args.pool:
    usage_pools=set(args.pool).intersection(usage_pools)

usage_pools = list(usage_pools)

date_fmt_list= {'day':"%Y-%m-%d", 'month':"%Y-%m", 'year':"%Y"}
sql_groupby_name = 'month'
if args.span:
    sql_groupby_name = args.span

date_fmt = date_fmt_list[sql_groupby_name]

# sum over all users for each pool
sum_usage_pools = map(lambda x: "sum(" + x + ")", usage_pools)
col_query = ','.join(sum_usage_pools)

# sum over all pools
if args.sum:
    col_query  = '(' + '+'.join(sum_usage_pools) + ')'
    usage_pools = ["total"]

project_data = {}

fig = plt.figure()

for project in usage_projects:
    sql_cmd = 'select strftime("' + date_fmt + '",enddate) as ' + sql_groupby_name + ',' + col_query + ' from usage where ' + 'userid in (select rowid from users where project=?) group by ' + sql_groupby_name 
    curs.execute(sql_cmd, (project,))
    project_data[project] = {'dates':[], 'usage':[]}

    rows = curs.fetchall()
    for row in rows:
        project_data[project]['dates'].append(datetime.datetime.strptime(row[0],date_fmt))
        project_data[project]['usage'].append(list(row[1:]))
    pool_idx = 0
    for temp in zip(*project_data[project]['usage']):
        if (max(temp) > 0):
            plt.plot_date(mpld.date2num(project_data[project]['dates']),array(temp),'-',xdate=True,label=project + " " + usage_pools[pool_idx])
        pool_idx += 1
        pool_idx = pool_idx % len(usage_pools)

#print project_data
plt.legend(loc='upper left')
plt.ylabel('cpu-hours per ' + sql_groupby_name)
fig.autofmt_xdate()
plt.show()
