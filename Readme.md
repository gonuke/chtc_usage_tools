CHTC Usage Tools
=================

A collection of tools to parse, store and visualize usage on CHTC resources.

parseUsage.py
-------------

Parse the daily CHTC usage by users table and store in a database:

**Syntax**

```
usage: parseUsage.py [-h] source database

A tool to place data into the usage db

positional arguments:
  source      A URI to a source of data. Must be one of html,ftp,file for a
              simple HTML file, or mbox for a mailbox of usage emails.
  database    An sqlite3 database file

optional arguments:
  -h, --help  show this help message and exit
```

**URI examples:**

* `mbox:local_file.mbox` is a local file in the mbox format, potentially with
  many daily email messages
* `file:local_file.html` is a local file containing a single set of daily usage
  data perhaps saved from the website
* `http://server.wisc.edu/usage_data.html` is a remote file containing a single set of daily usage data
    
`database`: an sqlite database file

**Comments**

From each daily report, the list of individual user data is parsed and stored in two tables of an SQLite database:

1. The `users` table:
   * `varchar(255) username`: as provided in the HTML table
   * `varchar(255) project`: as provided in the HTML table
   * the row number of each entry is used to provide an integer identifier for each user

2. The `usage` table:
   * `int userid`: an integer identifier for the user defined as the row of that user in the `users` table
   * `datetime enddate`: the date for the end of the daily statistics summary period
   * `int <poolname>`: one column for each computing pool

Each time a new table is parsed, new users may be added to the `users` table.  More importantly, if new compute pools are added, new columns are added to the `usage` table, and a default value of 0 is added for every prior entry in that column.

This script can read the tables from either a remote location (HTTP or FTP), a local file, or an `mbox` formatted mailbox.  For all but the `mbox` format, a single table is added with each invocation.  If an `mbox` is given as input, every message is parsed for an HTML payload that contains a user table.  All data is loaded into memory from each source before being written to the database.

For each date, the database is first checked for pre-existing data.  New data will NOT overwrite previous data.  No tools currently exist to replace old data with new data, other than direct SQL manipulation.


extractUsage.py
---------------

Extract and plot some standard views of data from a usage database.

**Syntax**

```
usage: extractUsage.py [-h] [--project [PROJECT [PROJECT ...]]]
                       [--pool [POOL [POOL ...]]] [-s]
                       [--span {day,month,year}]
                       database

A tool to extract usage data

positional arguments:
  database              The name of a database file

optional arguments:
  -h, --help            show this help message and exit
  --project [PROJECT [PROJECT ...]]
                        The name of a project over which to summarize the
                        results
  --pool [POOL [POOL ...]]
                        Limit the data to a single pool
  -s, --sum             Sum across pools
  --span {day,month,year}
                        Time span across which to sum data
```
