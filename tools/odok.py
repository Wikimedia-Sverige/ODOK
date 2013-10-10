#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Module for various means of communicating with the ODOK database

#----------------------------------------------------------------------------------------

import WikiApi as wikiApi
import MySQLdb
import dconfig as config
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
    def setUpApi(cls, user=config.odok_user, site=config.odok_site, verbose=False):
        '''
        Creates a OdokApi object
        '''
        #Provide url and identify (using e-mail)
        odok = cls('%s/api.php' %site,user)
        
        #Set reqlimit for odok
        odok.reqlimit = 50
        
        return odok
    
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
        
        #{"query":{"embeddedin":[{"pageid":5,"ns":0,"title":"Abbek\u00e5s"}]},"query-continue":{"embeddedin":{"eicontinue":"10|!|65"}}}
        for hit in jsonr['body']:
            members.append(hit['hit'])
        
        #print  "Fetching pages with ids: " + '|'.join(idList) + "...complete"
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
    
    def connectDatabase(self, edit=False):
        '''
        Connect to the mysql database, if it fails, go down in flames
        '''
        if edit:
            conn = MySQLdb.connect(host=config.db_server, db=config.db, user = config.db_edit, passwd = config.db_edit_password, use_unicode=True, charset='utf8')
        else:
            conn = MySQLdb.connect(host=config.db_server, db=config.db, user = config.db_read, passwd = config.db_read_password, use_unicode=True, charset='utf8')
        cursor = conn.cursor()
        return (conn, cursor)
    
    def closeConnections(self):
        '''
        Closes the connection to the database and closes the logfile
        '''
        self.conn.commit() 
        self.conn.close()
        self.flog.close()
    
    def __init__(self, edit=False, testing=False):
        '''
        Establish connection to database, set up logfile and determine testing
        '''
        self.flog = codecs.open('odokWriter.log','w','utf8') # logfile
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
        (self.conn, self.cursor) = self.connectDatabase(edit=edit)
#End of OdokSQL()

class OdokWriter(OdokSQL):
    @classmethod
    def setUp(self, testing=False):
        '''create an OdokWriter'''
        odok = cls(edit=True, testing=testing)
        return odok
    
    #some of OdokSQL.__init__ should probably be here instead to govern accessible fields
    #make a general updater/adder followed by more specific add artist etc. which requires a dict of a certain type and checks formating duplication etc.
    #make sure commit/respone handeling is done by the more general OdokSQL


class OdokReader(OdokSQL):
    @classmethod
    def setUp(self, testing=False):
        '''create an OdokReader'''
        odok = cls(edit=False, testing=testing)
        return odok
    
    #Special searches needed for new uploads and temporary searches not yet included in api
    #e.g.
    #ArtistApi:
    ##writeToDatabase.getArtistByWiki()

#End of OdokSQL()
