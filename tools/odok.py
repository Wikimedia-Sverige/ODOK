#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Module for various means of communicating with the ODOK database

#----------------------------------------------------------------------------------------

import WikiApi as wikiApi
import MySQLdb
#import pycurl

class OdokApi(wikiApi.WikiApi):
    '''
    When possible connect through the api
    Need to override setUpApi (but not apiaction by a lucky coincident)
    Should replace login/token/logout by dummyfunction to prevent these from being executed
    '''
    
    #dummy functions to prevent these from being executed
    def login(self, userName, userPass, verbose=True): dummyFunction(u'login')
    def setToken(self, token, verbose=True): dummyFunction(u'setToken')
    def setEditToken(self, verbose=True): dummyFunction(u'setEditToken')
    def clearEditToken(self): dummyFunction(u'clearEditToken')
    def logout(self): dummyFunction(u'logout')
    def dummyFunction(self, name):
        print u'%s() not supported by OdokApi' %name
        exit(2)
        
    @classmethod
    def setUpApi(cls, user, site, verbose=False):
        '''
        Creates a OdokApi object
        '''
        #Provide url and identify (using e-mail)
        odok = cls('%s/api.php' %site,user)
        
        #Set reqlimit for odok
        odok.reqlimit = 50
        
        return odok
    
    def apiaction(self, action):
        return self._apiurl + "?action=" + action + "&format=json&json=compact"
    
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
        #print "Fetching pages with ids: " + '|'.join(idList)
        #if no initial list supplied
        if members is None:
            members =[]
        
        #do an upper limit check and split into several requests if necessary
        reqlimit = self.limitByBytes(idList, self.reqlimit) #max reqlimit values per request but further limited by the bytelimit
        idList = list(set(idList)) #remove dupes
        if len(idList) > reqlimit:
            i=0
            while (i+reqlimit < len(idList)):
                reqlimit = self.limitByBytes(idList[i:], reqlimit) #tests if reqlimit is small enough
                self.getIds(idList[i:i+reqlimit], members, debug=debug)
                i=i+reqlimit
            #less than reqlimit left
            idList = idList[i:]
            if len(idList) < 1: #i.e. exactly divisible by reqlimit
                return members
        
        #Single run
        #action=query&list=embeddedin&cmtitle=Template:!
        jsonr = self.httpGET("get", [('id', '|'.join(idList).encode('utf-8')),
                                      ('limit', str(100))], debug=debug)
        
        if debug:
            print u'getIds(): idList=%s\n' %idList
            print jsonr
        
        #find errors
        if not jsonr['head']['status'] == '1':
            print self.failiure(jsonr)
            return None
        
        for hit in jsonr['body']:
            members.append(hit['hit'])
        
        return members
    
    def getQuery(self, queries, members=None, debug=False):
        '''
        Returns list of all objects matching the provided query (blunt function which should be avoided if possible)
        :param queries: A dictionary of parameter value pairs to limit the search by. THese must be formated and limited correctly
        :param members: (optional) A list to which to add the results (internal use)
        :return: list odok objects (dicts)
        '''
        #if no initial list supplied
        if members is None:
            members =[]
        
        #do a limited reqlimit check
        for k,v in queries.iteritems():
            v = v.split('|')
            reqlimit = self.limitByBytes(v, self.reqlimit)
            if len(v)> reqlimit:
                print '''getQuery() requires input to be correctly formated and limited\n
                         this request had %r/%r parameters for %s''' %(len(v), reqlimit, k)
                return None
        
        #Single run
        if not 'limit' in queries.keys():
            queries['limit'] = str(100)
        requestparams=[]
        for k,v in queries.iteritems():
            requestparams.append((k, v.encode('utf-8')))
        jsonr = self.httpGET("get", requestparams, debug=debug)

        if debug:
            print u'getQuery(): queries=%s\n' %queries
            print jsonr
        
        #find errors
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
    
#End of OdokApi()

class OdokSQL():
    '''
    Connection directly via SQL
    Use for editing database and for queries not (yet) supported by api
    Largely what is in odokWriter - still would be nice to split reading and writing
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
        conn = MySQLdb.connect(host=host, db=db, user=user, passwd=passwd, use_unicode=True, charset='utf8')
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
        #whitelist of editable tables. Excludes muni/county as these are largely inert
        self.tables={'main':'main_table', 'artist':'artist_table', 'source':'source_table', 'artist_links':'artist_links', 'aka':'aka_table'}
        #whitelist of editable parameters (per table)
        self.parameters={
            'main':[u'name', u'title', u'artist', u'descr', u'year', u'year_cmt', u'type', u'material', u'inside', u'address', u'county', u'muni', u'district', u'lat', u'lon', u'image', u'wiki_article', u'commons_cat', u'official_url', u'same_as', u'free', u'owner', u'cmt'],
            'artist':[u'first_name', u'last_name', u'wiki', u'birth_date', u'death_date', u'birth_year', u'death_year', u'creator', u'cmt'],
            'source':[u'name', u'wiki', u'real_id', u'url', u'cmt'],
            'artist_links':[u'object', u'artist'],
            'aka':[u'title', u'main_id']}
        #some parameters are only ok to add, not change
        self.insertParamters={
            'main':[u'id', u'source'],
            'artist':[u'id'],
            'source':[u'id'],
            'artist_links':[],
            'aka':[u'id']}
        self.testing=testing  # outputs to logfile instead of writing to database
        self.conn = None
        self.cursor = None
        (self.conn, self.cursor) = self.connectDatabase(host=host, db=db, user=user, passwd=passwd)
    
    def query(self, query, params, testing=False, expectReply=False):
        '''
        NEEDS to deal with no params (i.e. a commit) 
        Sends a query to the databse and returns the result
        :param query: the SQL safe query
        :param params: the parameters to stick into the query
        :param expectReply:if a reply from the execute statement is expected (e.g. from COUNT(*))
        :returns: list of rows
        '''
        if not params:
            params=tuple()
        elif not isinstance(params, tuple):
            params = (params,)
        
        if testing:
            self.log = u'%s\n%s' %(self.log, query %self.conn.literal(params))
            if expectReply: return (None,None)
            else: return None
        
        reply = self.cursor.execute(query, params)
        
        #return results
        result=[]
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
#End of OdokSQL()

class OdokWriter(OdokSQL):
    #some of OdokSQL.__init__ should probably be here instead to govern accessible fields
    #make a general updater/adder followed by more specific add artist etc. which requires a dict of a certain type and checks formating duplication etc.
    #make sure commit/respone handeling is done by the more general OdokSQL
    
    def updateTable(self, key, changes, table='main'):
        '''
        Makes a single update to the database
        :param table: table to update
        :param key: id to update
        :parm changes: list with {param:value}-pairs to be updated
        :return: None if successful
        '''
        if not table in self.tables.keys():
            self.log = self.log + u'updateTable: %s is not a valid table\n' %table
            return None
        elif not changes:
            self.log = self.log + u'updateTable: no changes given\n'
            return None
            
        query = u"""UPDATE %s SET""" %self.tables[table]
        vals=[]
        for k, v in changes.iteritems():
            if k in self.parameters[table]:
                query = u"""%s %s=%%s,""" %(query, k)
                vals.append(v)
            else:
                self.log = self.log + u'%s is not a valid parameter for %s\n' %(k, table)
        query = u"""%s WHERE id = %%s; """ %query[:-1]
        #break this out into OdokSQL.commit(self, query, vals)
        if self.testing:
            #not that this may give unicodeerror related to how literal works
            self.log = self.log + query %self.conn.literal(tuple(vals)+(key,)) + u'\n'
        else:
            try:
                self.cursor.execute(query, (tuple(vals)+(key,)))
                self.conn.commit()
            except MySQLdb.Warning, e:
                return e.message
        return None
    
    #def insertIntoTable(self, table, values):

class OdokReader(OdokSQL):
    #Special searches needed for new uploads and temporary searches not yet included in api
    #e.g.
    #ArtistApi:
    ##writeToDatabase.getArtistByWiki()
    
    def findAkas(self, idNo):
        '''
        given one id in main_table find and return the corresponding akas from aka_table
        SHOULD BE IN ApiGet
        '''
        q = u"""SELECT `id`, `title`, `main_id` FROM `aka_table` WHERE `main_id` = %s;"""
        rows = self.query(q, idNo)
        if len(rows) == 0:
            results = []
        else:
            results = []
            for r in rows:
                results.append({'id':str(r[0]), 'aka':r[1], 'main_id':r[2]})
        return results
    
    def findArtist(self, idNo):
        '''
        given one id in main_table find and return the corresponding artists from artist_table mapped via artist_links
        SHOULD BE IN ApiArtist
        '''
        q = u"""SELECT `id`, `first_name`, `last_name`, `wiki` FROM `artist_table` WHERE `id` IN 
                (SELECT a.`artist` FROM `artist_links` a WHERE a.`object` = %s);"""
        rows = self.query(q, idNo)
        if len(rows) == 0:
            results = []
        else:
            results = []
            for r in rows:
                results.append({'id':str(r[0]), 'first_name':r[1], 'last_name':r[2], 'wiki':r[3].upper()})
        return results
        
    def getArtistByWiki(self, wikidata):
        '''
        given a list of wikidata entities this checks id any are present in the artist_table
        :param wikidata: list of wikidataentities (or a single wikidata entity)
        :returns: dictionary of artist matching said entities with artistID as keys {first_name, last_name, wiki, birth_date, death_date, birth_year, death_year}
        SHOULD BE IN ApiArtist
        '''
        #if only one entity given
        if not isinstance(wikidata,list):
            if (isinstance(wikidata,str) or isinstance(wikidata,unicode)):
                wikidata = [wikidata,]
            else:
                print '"getArtistByWiki()" requires a list of wikidata entities or a single entity.'
                return None
        result = {}
        
        format_strings = ','.join(['%s'] * len(wikidata))
        q = u"""SELECT id, first_name, last_name, wiki, birth_date, death_date, birth_year, death_year FROM `artist_table` WHERE wiki IN (%s)""" % format_strings
        rows = self.query(q, tuple(wikidata))
        
        for r in rows:
            (artistID, first_name, last_name, wiki, birth_date, death_date, birth_year, death_year) = r
            result[str(artistID)] = {'first_name':first_name, 'last_name':last_name, 'wiki':wiki, 'birth_date':birth_date, 'death_date':death_date, 'birth_year':birth_year, 'death_year':death_year}
        
        return result

#End of OdokSQL()
