#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
'''
Module for various means of communicating with the ODOK database

To do for sql:
Switch over to SSCursor
'''

import WikiApi as wikiApi
import MySQLdb
# import pycurl

class OdokApi(wikiApi.WikiApi):
    '''
    When possible connect through the api
    Need to override setUpApi
    Should replace login/token/logout by dummyfunction to prevent
    these from being executed
    '''

    # dummy functions to prevent these from being executed
    def login(self, userName, userPass, verbose=True): self.dummyFunction(u'login')
    def setToken(self, token, verbose=True): self.dummyFunction(u'setToken')
    def setEditToken(self, verbose=True): self.dummyFunction(u'setEditToken')
    def clearEditToken(self): self.dummyFunction(u'clearEditToken')
    def logout(self): self.dummyFunction(u'logout')
    def dummyFunction(self, name):
        print u'%s() not supported by OdokApi' % name
        exit(2)

    @classmethod
    def setUpApi(cls, user, site, scriptidentify=u'OdokBot/0.5', verbose=False):
        '''
        Creates a OdokApi object
        '''
        # Provide url and identify (using e-mail)
        odok = cls('%s/api.php' % site, user, scriptidentify)

        # Set reqlimit for odok
        odok.reqlimit = 50

        return odok

    def apiaction(self, action, form=None):
        if not form:
            return self._apiurl + "?action=" + action + "&format=json&json=compact"
        else:
            return self._apiurl + "?action=" + action + "&format=" + form

    def failiure(self, jsonr, debug=False):
        '''
        Standardised function to present errors
        '''
        return (jsonr['head']['error_number'], jsonr['head']['error_message'])

    def getIds(self, idList, members=None, debug=False):
        '''
        Returns list of all objects matching one of the provided ids
        :param idList: A list of ids to look for
        :param members: (optional) A list to which to add the results (internal use)
        :return: list odok objects (dicts)
        '''
        # print "Fetching pages with ids: " + '|'.join(idList)
        # if no initial list supplied
        if members is None:
            members = []

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.limitByBytes(idList, self.reqlimit)  # max reqlimit values per request but further limited by the bytelimit
        idList = list(set(idList))  # remove dupes
        if len(idList) > reqlimit:
            i = 0
            while (i+reqlimit < len(idList)):
                reqlimit = self.limitByBytes(idList[i:], reqlimit)  # tests if reqlimit is small enough
                self.getIds(idList[i:i+reqlimit], members, debug=debug)
                i += reqlimit
            # less than reqlimit left
            idList = idList[i:]
            if len(idList) < 1:  # i.e. exactly divisible by reqlimit
                return members

        # Single run
        # action=query&list=embeddedin&cmtitle=Template:!
        jsonr = self.httpGET("get", [('id', '|'.join(idList).encode('utf-8')),
                                     ('limit', str(100))], debug=debug)

        if debug:
            print u'getIds(): idList=%s\n' % idList
            print jsonr

        # find errors
        if not jsonr['head']['status'] == '1':
            print self.failiure(jsonr)
            return None

        for hit in jsonr['body']:
            members.append(hit['hit'])

        return members

    def getAllLists(self, members=None, offset=None, debug=False):
        '''
        Returns list of all wikidata ids corresponding to known lists
        :param members: (optional) A list to which to add the results (internal use)
        :param offset: (optional) Offset within the current batch of results
        :return: list of wikidata ids
        '''
        if members is None:
            members = []

        # Single run
        requestparams = [('limit', str(100)),
                         ('function', 'lists'.encode('utf-8'))]
        if offset:
            requestparams.append(('offset', str(offset)))

        jsonr = self.httpGET("admin", requestparams, debug=debug)

        if debug:
            print u'getAllLists(): \n'
            print jsonr

        # find errors
        if not jsonr['head']['status'] == '1':
            print self.failiure(jsonr)
            return None

        for hit in jsonr['body']:
            members.append(hit['hit']['list'])

        if 'continue' in jsonr['head'].keys():
            offset = jsonr['head']['continue']
            members = self.getAllLists(members, offset, debug=debug)

        return members

    def getListMembers(self, idList, members=None, offset=None, show=None, debug=False):
        '''
        Returns list of all objects matching one of the provided list ids
        :param idList: A list of list ids to look for
        :param members: (optional) A list to which to add the results (internal use)
        :param offset: (optional) Offset within the current batch of results
        :param show: (optional) A list of fields to return
        :return: list odok objects (dicts)
        '''
        # print "Fetching pages with ids: " + '|'.join(idList)
        # if no initial list supplied
        if members is None:
            members = []

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.limitByBytes(idList, self.reqlimit)  # max reqlimit values per request but further limited by the bytelimit
        idList = list(set(idList))  # remove dupes
        if len(idList) > reqlimit:
            i = 0
            while (i+reqlimit < len(idList)):
                reqlimit = self.limitByBytes(idList[i:], reqlimit)  # tests if reqlimit is small enough
                self.getListMembers(idList[i:i+reqlimit], members, offset, show=show, debug=debug)
                i += reqlimit
            # less than reqlimit left
            idList = idList[i:]
            if len(idList) < 1:  # i.e. exactly divisible by reqlimit
                return members

        # Single run
        query = [('limit', str(100)),
                 ('list', '|'.join(idList).encode('utf-8'))]
        if show:
            query += [('show', '|'.join(show).encode('utf-8'))]
        if offset:
            query += [('offset', str(offset))]

        jsonr = self.httpGET("get", query, debug=debug)

        if debug:
            print u'getListMembers(): idList=%s\n' % idList
            print jsonr

        # find errors
        if not jsonr['head']['status'] == '1':
            print self.failiure(jsonr)
            return None

        for hit in jsonr['body']:
            members.append(hit['hit'])

        if 'continue' in jsonr['head'].keys():
            offset = jsonr['head']['continue']
            members = self.getListMembers(idList, members, offset,
                                          show=show, debug=debug)

        return members

    def getQuery(self, queries, members=None, debug=False):
        '''
        Returns list of all objects matching the provided query (blunt
        function which should be avoided if possible)
        :param queries: A dictionary of parameter value pairs to limit
            the search by. These must be formated and limited correctly
        :param members: (optional) A list to which to add the results
            (internal use)
        :return: list odok objects (dicts)
        '''
        # if no initial list supplied
        if members is None:
            members = []

        # do a limited reqlimit check
        for k, v in queries.iteritems():
            v = v.split('|')
            reqlimit = self.limitByBytes(v, self.reqlimit)
            if len(v) > reqlimit:
                print '''getQuery() requires input to be correctly formated and limited\n
                         this request had %r/%r parameters for %s''' % (len(v), reqlimit, k)
                return None

        # Single run
        if 'limit' not in queries.keys():
            queries['limit'] = str(100)
        requestparams = []
        for k, v in queries.iteritems():
            requestparams.append((k, v.encode('utf-8')))
        jsonr = self.httpGET("get", requestparams, debug=debug)

        if debug:
            print u'getQuery(): queries=%s\n' % queries
            print jsonr

        # find errors
        if not jsonr['head']['status'] == '1':
            print self.failiure(jsonr)
            return None

        for hit in jsonr['body']:
            members.append(hit['hit'])

        if 'continue' in jsonr['head'].keys():
            offset = jsonr['head']['continue']
            queries['offset'] = str(offset)
            self.getQuery(queries, members=members, debug=debug)

        return members

    def getGeoJson(self, members=None, full=False, source=None, offset=0, inside=False, removed=False, same_as=False, has_list=True, debug=False):
        '''
        Returns list of all objects matching one of the provided ids
        :param members: (optional) A list to which to add the results (internal use)
        :param full: (optional) Whether to get the full geojson profile
        :param source: (optional) Limits the objects to only those from a named source
        :param offset: (optional) Sets offset to get later results (internal use)
        :param inside: (optional) Whether to include objects tagged as inside
        :param remove: (optional) Whether to include objects tagged as removed
        :param same_as: (optional) Whether to include objects tagged as having a same_as
        :param has_list: (optional) Whether to require objects to have a non-empty list parameter
        :return: list odok objects (dicts)
        '''
        # if no initial list supplied
        if members is None:
            members = []

        query = [('limit', str(100)),
                 ('offset', str(offset))]
        if full:
            query += [('geojson', 'full')]
        if source:
            query += [('source', str(source))]
        if not inside:
            query += [('is_inside', 'false')]
        if not removed:
            query += [('is_removed', 'false')]
        if not same_as:
            query += [('has_same', 'false')]
        if has_list:
            query += [('has_list', 'true')]

        # Single run
        # action=get&limit=100&format=geojson&geojson=full&offset=0
        jsonr = self.httpGET("get", query, form="geojson", debug=debug)

        if debug:
            print u'getGeoJson()\n'
            print jsonr

        # find errors
        if not jsonr['head']['status'] == '1':
            print self.failiure(jsonr)
            return None

        for feature in jsonr['features']:
            members.append(feature)

        if 'continue' in jsonr['head'].keys():
            offset = jsonr['head']['continue']
            members = self.getGeoJson(members=members, full=full,
                                      source=source, offset=offset,
                                      inside=inside, removed=removed,
                                      same_as=same_as, debug=debug)

        return members
# End of OdokApi()


class OdokSQL():
    '''
    Connection directly via SQL
    Use for editing database and for queries not (yet) supported by api
    Largely what was in odokWriter
    Maybe:
    file odok.py
    class OdokApi(wikiApi.WikiApi)
    class OdokSQL()-abstract
    class OdokWriter(OdokSQL)
        edit=True
    class OdokReader(OdokSQL)
        edit=False
    '''

    def connectDatabase(self, host, db, user, passwd):
        '''
        Connect to the mysql database, if it fails, go down in flames
        '''
        conn = MySQLdb.connect(host=host, db=db, user=user, passwd=passwd,
                               use_unicode=True, charset='utf8')
        cursor = conn.cursor()
        return (conn, cursor)

    def closeConnections(self):
        '''
        Closes the connection to the database and returns the logfile
        '''
        self.conn.commit()
        self.conn.close()
        return self.log

    def __init__(self, host, db, user, passwd, testing=False):
        '''
        Establish connection to database, set up logfile and determine testing
        '''
        self.log = u''
        # whitelist of editable tables
        # Excludes muni/county as these are largely inert
        self.tables = {
            'main': 'main_table',
            'artist': 'artist_table',
            'source': 'source_table',
            'artist_links': 'artist_links',
            'aka': 'aka_table'}
        # whitelist of editable parameters (per table)
        self.parameters = {
            'main': [u'name', u'title', u'artist', u'descr', u'year',
                     u'year_cmt', u'type', u'material', u'inside',
                     u'address', u'county', u'muni', u'district', u'lat',
                     u'lon', u'removed', u'image', u'wiki', u'list',
                     u'commons_cat', u'official_url', u'same_as', u'free',
                     u'owner', u'cmt'],
            'artist': [u'first_name', u'last_name', u'wiki', u'birth_date',
                       u'death_date', u'birth_year', u'death_year', u'creator',
                       u'cmt'],
            'source': [u'name', u'wiki', u'real_id', u'url', u'cmt'],
            'artist_links': [u'object', u'artist'],
            'aka': [u'title', u'main_id']}
        # some parameters are only ok to add, not change
        self.insertParamters = {
            'main': [u'id', u'source'],
            'artist': [u'id'],
            'source': [u'id'],
            'artist_links': [],
            'aka': [u'id']}
        self.testing = testing  # output to logfile instead of writing to db
        self.conn = None
        self.cursor = None
        (self.conn, self.cursor) = self.connectDatabase(host=host, db=db, user=user, passwd=passwd)

    def resetLog(self):
        '''
        returns current log content then resets the log
        :return: string
        '''
        oldLog = self.log
        self.log = u''
        return oldLog

    def multiQuery(self, queries):
        '''
        Multiple queries where executemany is not suitable and multiple
        executes are needed (e.g. when using LAST_INSERT_ID()) to avoid
        "Commands out of sync"
        To do: Add support for params
        :param queries: List of SQL safe queries
        '''
        results = []
        if not isinstance(queries, list):
            print u'multiQuery requires a list of queries without parameters'
            return None

        for q in queries:
            results.append(self.query(query=q, params=None))
        self.conn.commit()
        return results

    def query(self, query, params, expectReply=False, commit=False):
        '''
        NEEDS to deal with no params (i.e. a commit)
        Sends a query to the databse and returns the result
        :param query: the SQL safe query
        :param params: the parameters to stick into the query
        :param expectReply: if a reply from the execute statement is \
                            expected (e.g. from COUNT(*))
        :param commit: if a conn.commit step should be taken (potentially \
                       useful when writing to db)
        :returns: list of rows
        '''
        if not params:
            params = tuple()
        elif not isinstance(params, tuple):
            params = (params,)

        if self.testing:
            self.log = u'%s\n%s' % (self.log,
                                    query % self.conn.literal(params))
            if expectReply:
                return (None, None)
            else:
                return None

        # run query
        try:
            reply = self.cursor.execute(query, params)
            if commit:
                self.conn.commit()
        except MySQLdb.Warning, e:
            raise e.message

        # return results
        result = []
        row = self.cursor.fetchone()
        while row is not None:
            result.append(row)
            row = self.cursor.fetchone()

        if expectReply:
            return (reply, result)
        else:
            return result

    @classmethod
    def setUp(cls, host, db, user, passwd, testing=False):
        '''create an OdokSQL object'''
        odok = cls(host=host, db=db, user=user, passwd=passwd, testing=testing)
        return odok
# End of OdokSQL()


class OdokWriter(OdokSQL):
    # TODO
    # some of OdokSQL.__init__ should probably be here instead to govern
    #    accessible fields
    # make a general updater/adder followed by more specific add artist
    #    etc. which requires a dict of a certain type and checks formating,
    #    duplication etc.
    # make sure commit/respone handeling is done by the more general OdokSQL

    def updateTable(self, key, changes, table='main'):
        '''
        Makes a single update to the database
        :param table: table to update
        :param key: id to update
        :parm changes: list with {param:value}-pairs to be updated
        :return: None if successful
        '''
        if table not in self.tables.keys():
            self.log += u'updateTable: %s is not a valid table\n' % table
            return None
        elif not changes:
            self.log += u'updateTable: no changes given\n'
            return None

        query = u"""UPDATE %s SET""" % self.tables[table]
        vals = []
        for k, v in changes.iteritems():
            if k in self.parameters[table]:
                query = u"""%s %s=%%s,""" % (query, k)
                vals.append(v)
            else:
                self.log += u'%s is not a valid parameter for %s\n' % (k, table)
        query = u"""%s WHERE id = %%s; """ % query[:-1]

        # run and return any error
        try:
            self.query(query, tuple(vals)+(key,), commit=True)
        except MySQLdb.Warning, e:
            return e.message

    def clearListEntries(self, wikidata):
        '''
        Removes all references to a given set of lists
        :param wikidata: a list of wikidata ids to on-wiki lists
        :return: None if successful
        '''
        if not isinstance(wikidata, list):
            if isinstance(wikidata, (str, unicode)):
                wikidata = [wikidata, ]
            else:
                return '"clearListEntries()" requires a list of wikidata \
                         entities or a single entity.'
        if not len(wikidata) > 0:
            return None

        format_strings = ','.join(['%s'] * len(wikidata))
        q = u"""UPDATE `main_table`
                SET `list` = ''
                WHERE `list` IN (%s);""" % format_strings

        # run and return any error
        try:
            self.query(q, tuple(wikidata), commit=True)
        except MySQLdb.Warning, e:
            return e.message

    def insertIntoTable(self, table, values):
        '''
        Insert a single update to the database
        :param table: table to update
        :param values: list with {param:value}-set to be added,
            must contain all keys in self.parameters[table],
            all others are ignored
        :return: None if successful
        '''
        if table not in self.tables.keys():
            self.log += u'insertIntoTable: %s is not a valid table\n' % table
            return None
        elif not values or len(values) == 0:
            self.log += u'insertIntoTable: no values given\n'
            return None

        query = u"""INSERT INTO %s (%s) VALUES""" % (self.tables[table],
                                                     ','.join(self.parameters[table]))
        row = u','.join(['%s']*len(self.parameters[table]))
        vals = []
        for v in values:
            if sorted(v.keys()) == sorted(self.parameters[table]):
                query = u"""%s (%s),""" % (query, row)
                for p in self.parameters[table]:
                    vals.append(v[p])
            else:
                self.log += u'insertIntoTable: a required parameter is \
                              missing for table %s (given: %s; required: \
                              %s)\n' % (table,
                                        ','.join(v.keys()),
                                        ','.join(self.parameters[table]))
        query = query[:-1]

        # run and return any error
        try:
            self.query(query, tuple(vals), commit=True)
        except MySQLdb.Warning, e:
            return e.message


class OdokReader(OdokSQL):
    '''
    Special searches needed for new uploads and temporary searches not
    yet included in api e.g.
    ArtistApi:
    replaces: writeToDatabase.getArtistByWiki()
    '''

    def findAkas(self, idNo):
        '''
        given one id in main_table find and return the corresponding
        akas from aka_table
        SHOULD BE IN ApiGet
        '''
        q = u"""SELECT `id`, `title`, `main_id`
                FROM `aka_table`
                WHERE `main_id` = %s;"""
        rows = self.query(q, idNo)
        if len(rows) == 0:
            results = []
        else:
            results = []
            for r in rows:
                results.append({'id': str(r[0]), 'aka': r[1], 'main_id': r[2]})
        return results

    def findArtist(self, idNo):
        '''
        given one id in main_table find and return the corresponding artists
        from artist_table mapped via artist_links
        SHOULD BE IN ApiArtist [now in api.php?action=artist&artwork=<id>]
        '''
        q = u"""SELECT `id`, `first_name`, `last_name`, `wiki`
                FROM `artist_table`
                WHERE `id` IN
                    (SELECT a.`artist`
                     FROM `artist_links` a
                     WHERE a.`object` = %s);"""
        rows = self.query(q, idNo)
        if len(rows) == 0:
            results = []
        else:
            results = []
            for r in rows:
                results.append({'id': str(r[0]), 'first_name': r[1],
                                'last_name': r[2], 'wiki': r[3].upper()})
        return results

    def getArtistByWiki(self, wikidata):
        '''
        given a list of wikidata entities this checks if any are present
        in the artist_table
        :param wikidata: list of wikidataentities (or a single wikidata entity)
        :returns: dictionary of artist matching said entities with artistID as
        keys {first_name, last_name, wiki, birth_date, death_date, birth_year, death_year}
        SHOULD BE IN ApiArtist [now in api.php?action=artist&wiki=<id>]
        '''
        # if only one entity given
        if not isinstance(wikidata, list):
            if isinstance(wikidata, (str, unicode)):
                wikidata = [wikidata, ]
            else:
                print '"getArtistByWiki()" requires a list of wikidata entities or a single entity.'
                return None
        # remove empties
        if '' in wikidata:
            wikidata.remove('')
        if len(wikidata) == 0:
            return None
        result = {}

        format_strings = ','.join(['%s'] * len(wikidata))
        q = u"""SELECT id, first_name, last_name, wiki, birth_date, death_date, birth_year, death_year
                FROM `artist_table`
                WHERE wiki IN (%s);""" % format_strings
        # print q %self.conn.literal(tuple(wikidata))
        rows = self.query(q, tuple(wikidata))

        for r in rows:
            (artistID, first_name, last_name, wiki, birth_date, death_date, birth_year, death_year) = r
            result[str(artistID)] = {'first_name': first_name,
                                     'last_name': last_name,
                                     'wiki': wiki,
                                     'birth_date': birth_date,
                                     'death_date': death_date,
                                     'birth_year': birth_year,
                                     'death_year': death_year}

        return result

# End of OdokReader()
