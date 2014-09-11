import sqlite3

def usage_db_connect(dbfile='chtc_usage.db'):
    conn = sqlite3.connect(dbfile)
    return conn

def get_db_pools(curs):
    """get list of columns already in usage table"""
    curs.execute('select * from usage')
    columns = map(lambda x: x[0], curs.description)
    db_pools = columns[2:]
    return db_pools


def get_db_projects(curs):
    """get list of proejcts already in user table"""
    curs.execute('select project from users')
    rows = curs.fetchall()
    db_projects = []
    for row in rows:
        db_projects.append(row[0])
    return db_projects
