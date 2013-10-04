#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# PyCJWiki Basic
# Based on PyCJWiki Version 1.31 (C) by Smallman12q (https://en.wikipedia.org/wiki/User_talk:Smallman12q) GPL, see <http://www.gnu.org/licenses/>.
# Requires python2.7, ujson, and PyCurl

#----------------------------------------------------------------------------------------

import pycurl, ujson, cStringIO
import time
import traceback

class WikiApi(object):
    
    class Delay:
        """
            Delay enum, the delays for requests etc.
            Delay implemented as sleep before given request...could be improved
        """
        ALLREQUESTS = 0
        UPLOAD = 0
    
    #useragenturl and contact in unicode
    #
    def __init__(self, apiurl, useragentidentify):
        """
        :param apiurl: The url of the api.php such as https://commons.wikimedia.org/w/api.php
            Pass as str
        :param useragentidentify: The identification to be sent in the header.
            Such as u'https://commons.wikimedia.org/wiki/User_talk:Smallman12q'
            Part of https://www.mediawiki.org/wiki/Api#Identifying_your_client
            Pass as u
        """

        #Wiki vars
        self._apiurl = apiurl
        self.userName = None
        self.tokens = []
        self.edittoken = None

        #Response buffer
        self.responsebuffer= cStringIO.StringIO()
        self.clearresponsebufferafterresponse = False #True will clear, and save memory, but less useful if error

        #Set up reusable curl connection
        self.sitecurl=pycurl.Curl()
        self.sitecurl.setopt(pycurl.WRITEFUNCTION, self.responsebuffer.write) #Writes to response buffer
        self.sitecurl.setopt(pycurl.COOKIEFILE, "") #Use in-memory cookie
        self.sitecurl.setopt(pycurl.USERAGENT, 'OdokBot/0.5 (' + useragentidentify.encode('utf-8') + ')')
        self.sitecurl.setopt(pycurl.POST, 1)
        self.sitecurl.setopt(pycurl.CONNECTTIMEOUT, 60)
        self.sitecurl.setopt(pycurl.TIMEOUT, 120)
        self.sitecurl.setopt(pycurl.ENCODING, 'gzip, deflate')
        self.sitecurl.setopt(pycurl.HTTPHEADER,["Expect:", "Connection: Keep-Alive", "Keep-Alive: 60"])
        #self.sitecurl.setopt(pycurl.PROXY, 'http://localhost:8888') #Proxy if needed
    
    
    def httpPOST(self, action, params, depth=0, timeoutretry=0):
        """

        :param action: The action, pass as str
        :param params: The params to be posted
        :param depth: A counter used for recursive failed stashes
        :param timeoutretry: A counter for timeoutretries
        :return:
        """
        #Clear response buffer
        self.responsebuffer.truncate(0)

        #Set curl http request
        self.sitecurl.setopt(pycurl.URL, self.apiaction(action))
        self.sitecurl.setopt(pycurl.HTTPPOST, params)

        #Try the curl http request
        try:
            time.sleep(self.Delay.ALLREQUESTS)
            self.sitecurl.perform()
        except pycurl.error, error:
            errno, errstr = error
            print( 'An error occurred: ' + str(errno) + ':', errstr)
            traceback.print_exc()

            #Response Timed Out, Retry up to 3 times
            if(errno == 28):
                if(timeoutretry < 3):
                    time.sleep(2)
                    self.httpPOST(action,params,depth,timeoutretry=(timeoutretry+1))
        
        #print self.responsebuffer.getvalue()
        json = ujson.loads(self.responsebuffer.getvalue())
        if "servedby" in json: #Some sort of error
            if "error" in json:
                if "code" in json["error"]:
                    #Bug 36587
                    if json["error"]["code"] == "internal_api_error_UploadChunkFileException":
                        if(depth < 3):
                            time.sleep(2)
                            self.httpPOST(action,params,(depth + 1))
            #maybe throw something?
        
        if self.clearresponsebufferafterresponse:
            self.responsebuffer.truncate(0)

        return json
    
    def printResponseBuffer(self):
        print self.responsebuffer.getvalue()
    
    #username,userpass unicode
    def login(self, userName, userPass, verbose=True):
        """
        :param userName: username as u
        :param userPass: userpassword as u. Not stored after login
        :return:
        :eturns type:
        """
        if verbose:
            print "Logging into " + self._apiurl + " as " + userName
            print "Logging in...(1/2)"
        
        #Login
        jsonr = self.httpPOST("login", [('lgname', userName.encode('utf-8')),
                                        ('lgpassword', userPass.encode('utf-8'))])
        if 'NeedToken' in jsonr['login']['result']:
            if verbose: print "Logging in...(1/2)...Success!"
        else:
            print "Logging in...(1/2)...Failed."
            self.printResponseBuffer()
            exit()
        
        #Login 2/2
        if verbose: print "Logging in...(2/2)"
        jsonr = self.httpPOST("login", [('lgname', userName.encode('utf-8')),
                                        ('lgpassword', userPass.encode('utf-8')),
                                        ('lgtoken',str(jsonr['login']['token']))])
        if 'Success' in jsonr['login']['result']:
            if verbose: print "Logging in...(2/2)...Success!"
        
        else :
            print "Logging in...(2/2)...Failed"
            self.printResponseBuffer()
            exit()
        
        self.userName = userName #Now logged in
        if verbose: print "You are now logged in as " + self.userName
    
    def setToken(self, token, verbose=True):
        if verbose: print "Retrieving token: " + token
        jsonr = self.httpPOST("tokens", [('type', str(token))])
        if(jsonr['tokens']['edittoken'] == "+\\"):
            print "Edit token not set."
            self.printResponseBuffer()
            exit()
        else:
            self.edittoken = str(jsonr['tokens']['edittoken'])
            if verbose: print "Edit token retrieved: " + self.edittoken
    
    def setEditToken(self, verbose=True):
        self.setToken('edit', verbose=verbose)
    
    def clearEditToken(self):
        self.edittoken = None
        #TODO Clear in tokens dict when implemented
    
    def getTimestamp(self, article, debug=False):
        '''
        Returns the timestamp of (the latest revision of) the provided article
        :parameter article: pagetitle to look at
        :return: timestamp as string in ISO 8601 format
        '''
        jsonr = self.httpPOST("query", [('prop', 'revisions'),
                                        ('titles', article.encode('utf-8')),
                                        ('rvprop', 'timestamp'),
                                        ('rvlimit', '1')])
        if debug:
            print u'getTimestamp(): article=%s\n' %article
            print jsonr
        
        pageid = jsonr['query']['pages'].keys()[0]
        if pageid == u'-1':
            print 'no entry for "%s"' %article
            return None
        else:
            return jsonr['query']['pages'][pageid]['revisions'][0]['timestamp']
    
    def getEmbeddedin(self, templatename, einamespace, debug=False):
        '''
        Returns list of all pages embeding a given template
        :param templatename: The template to look for (including "Template:")
        :param einamespace: namespace to limit the search to (0=main)
        :return: list containing pagenames
        '''
        
        print "Fetching pages embeding: " + templatename
        members = []
        #action=query&list=embeddedin&cmtitle=Tempålate:!
        jsonr = self.httpPOST("query", [('list', 'embeddedin'),
                                        ('eititle', templatename.encode('utf-8')),
                                        ('einamespace', str(einamespace)),
                                        ('eilimit', '500')])
        if debug:
            print u'getEmbeddedin(): templatename=%s\n' %templatename
            print jsonr
        
        #{"query":{"embeddedin":[{"pageid":5,"ns":0,"title":"Abbek\u00e5s"}]},"query-continue":{"embeddedin":{"eicontinue":"10|!|65"}}}
        for page in jsonr['query']['embeddedin']:
            members.append((page['title']))
        
        while 'query-continue' in jsonr:
            print  "Fetching pages embeding: " + templatename + "...fetching more"
            #print jsonr['query-continue']['embeddedin']['eicontinue']
            jsonr = self.httpPOST("query", [('list', 'embeddedin'),
                                            ('eititle', templatename.encode('utf-8')),
                                            ('eilimit', '500'),
                                            ('einamespace', str(einamespace)),
                                            ('eicontinue', str(jsonr['query-continue']['embeddedin']['eicontinue']))])
            for page in jsonr['query']['embeddedin']:
                members.append((page['title']))
        
        print  "Fetching pages embeding: " + templatename + "...complete"
        return members
    
    def getEmbeddedinTimestamps(self, templatename, einamespace, debug=False):
        '''
        Returns a list of all pages embeding a given template along with the timestamp for when it was last edited
        combines getEmbeddedin() and getTimestamps()
        :param templatename: The template to look for (including "Template:")
        :param einamespace: namespace to limit the search to (0=main)
        :return: list containing dicts {pagename, timestamp} where timestamp is a string in ISO 8601 format
        '''
        
        print "Fetching pages embeding: " + templatename
        members = []
        #action=query&prop=revisions&format=json&rvprop=timestamp&generator=embeddedin&geititle=Mall%3A!&geinamespace=0&geilimit=500
        jsonr = self.httpPOST("query", [('prop', 'revisions'),
                                        ('rvprop', 'timestamp'),
                                        ('generator', 'embeddedin'),
                                        ('geititle', templatename.encode('utf-8')),
                                        ('geinamespace', str(einamespace)),
                                        ('geilimit', '500')])
        if debug:
            print u'getEmbeddedinTimestamps() templatename:%s \n' %templatename
            print jsonr
        
        #{"query-continue":{"embeddedin":{"geicontinue":"10|Offentligkonstlista|1723456"}},"query":{"pages":{"1718037":{"pageid":1718037,"ns":0,"title":"Lista...","revisions":[{"timestamp":"2013-08-24T13:01:49Z"}]}}}}
        for page in jsonr['query']['pages']:
            page = jsonr['query']['pages'][page]
            members.append({'title':page['title'], 'timestamp':page['revisions'][0]['timestamp']})
        
        while 'query-continue' in jsonr:
            print  "Fetching pages embeding: " + templatename + "...fetching more"
            #print jsonr['query-continue']['embeddedin']['geicontinue']
            jsonr = self.httpPOST("query", [('prop', 'revisions'),
                                        ('rvprop', 'timestamp'),
                                        ('generator', 'embeddedin'),
                                        ('geititle', templatename.encode('utf-8')),
                                        ('geinamespace', str(einamespace)),
                                        ('geilimit', '500'),
                                        ('geicontinue',str(jsonr['query-continue']['embeddedin']['geicontinue']))])
            for page in jsonr['query']['pages']:
                page = jsonr['query']['pages'][page]
                members.append({'title':page['title'], 'timestamp':page['revisions'][0]['timestamp']})
        
        print  "Fetching pages embeding: " + templatename + "...complete"
        return members
    
    def getPageInfo(self, articles, dDict=None, debug=False):
        '''
        Given a list of articles this tells us if the page is either
        * Non-existent (red link)
        * A redirect (and returns real page)
        * A disambiguity page
        * Normal page
        and whether the page corresponds to a wikidata entry (and returns the wikidata id)
        :param articles: a list of pagenames (or a single pagename) to look at
        :param dDict: (optional) a dict object into which output is placed
        :return: a dict with the supplied pagenames as keys and a each value being a dict of corresponding properties with possible parameters being: redirected, missing, disambiguation, wikidata
        '''
        #if only one article given
        if not isinstance(articles,list):
            if (isinstance(article,str) or isinstance(article,unicode)):
                articles = [articles,]
            else:
                print '"getPageInfo" requires a list of pagenames or a single pagename.'
                return None
        
        #if no initial dict suplied
        if dDict is None:
            dDict ={}
        
        #do an upper limit check and split into several requests if necessary
        reqlimit = 50 #max 50 titles per request allowed
        articles = list(set(articles)) #remove dupes
        if len(articles) > reqlimit:
            i=0
            while (i+reqlimit < len(articles)):
                self.getPageInfo(articles[i:i+reqlimit], dDict, debug=debug)
                i=i+reqlimit
            #less than reqlimit left
            articles = articles[i:]
            if len(articles) < 1: #i.e. exactly divisible by reqlimit
                return dDict
        
        #Single run
        jsonr = self.httpPOST("query", [('prop', 'pageprops'),
                                    ('redirects', ''),
                                    ('titles', '|'.join(articles).encode('utf-8'))])
        if debug:
            print u'getPageInfo(): articles=%s\n' %'|'.join(articles)
            print jsonr
        
        #start with redirects
        rDict = {}
        if 'redirects' in jsonr['query'].keys():
            redirects = jsonr['query']['redirects'] #a list
            for r in redirects:
                rDict[r['to']] = r['from']
        
        #then pages
        pages = jsonr['query']['pages'] #a dict
        for k, v in pages.iteritems():
            page = {}
            title = v['title']
            #check if redirected
            if title in rDict.keys():
                page['redirect'] = title
                title = rDict[title]
            #missing
            if 'missing' in v.keys():
                page['missing'] = True
            #properties
            if 'pageprops' in v.keys():
                u = v['pageprops']
                if 'disambiguation' in u.keys():
                    page['disambiguation'] = True
                if 'wikibase_item' in u.keys():
                    page['wikidata'] = u['wikibase_item'].upper()
            dDict[title] = page.copy()
        
        return dDict #in case one was not supplied
    
    def getPage(self, articles, dDict=None, debug=False):
        '''
        Given an article this returns the contents of (the latest revision of) the page
        :param articles: a list of pagenames (or a single pagename) to look at
        :param dDict: (optional) a dict object into which output is placed
        :return: dict of contents with pagenames as key
        '''
        #if only one article given
        if not isinstance(articles,list):
            if (isinstance(article,str) or isinstance(article,unicode)):
                articles = [articles,]
            else:
                print '"getPage()" requires a list of pagenames or a single pagename.'
                return None
        
        #if no initial dict suplied
        if dDict is None:
            dDict ={}
        
        #do an upper limit check and split into several requests if necessary
        reqlimit = 50 #max 50 titles per request allowed
        articles = list(set(articles)) #remove dupes
        if len(articles) > reqlimit:
            i=0
            while (i+reqlimit < len(articles)):
                self.getPage(articles[i:i+reqlimit], dDict, debug=debug)
                i=i+reqlimit
            #less than reqlimit left
            articles = articles[i:]
            if len(articles) < 1: #i.e. exactly divisible by reqlimit
                return dDict
        
        #Single run
        jsonr = self.httpPOST("query", [('prop', 'revisions'),
                                    ('rvprop', 'content'),
                                    ('titles', '|'.join(articles).encode('utf-8'))])
        if debug:
            print u'getPage() : articles= %s\n' %'|'.join(articles)
            print jsonr
        
        for page in jsonr['query']['pages']:
            if int(page) <0: #Either missing or invalid
                dDict[jsonr['query']['pages'][page]['title']] = None
            else:
                dDict[jsonr['query']['pages'][page]['title']] = jsonr['query']['pages'][page]['revisions'][0]['*']
        
        return dDict #in case one was not supplied
    
    def editText(self, title, newtext, comment, minor=False,bot=True,userassert='bot', nocreate=False, debug=False):
        print("Editing " + title.encode('utf-8','ignore'))
        requestparams = [('title',  title.encode('utf-8')),
                         ('text', newtext.encode('utf-8')),
                         ('summary', comment.encode('utf-8')),
                         ('token', str(self.edittoken))]
        if minor:
            requestparams.append(('minor', 'true'))
        if bot:
            requestparams.append(('bot', 'true'))
        if userassert is not None:
            requestparams.append(('assert', userassert))
        if nocreate:
            requestparams.append(('nocreate','true'))

        jsonr = self.httpPOST("edit", requestparams)
        if debug:
            print u'editText(): title=%s\n' %title
            print jsonr
        
        if 'edit' in jsonr:
            if(jsonr['edit']['result'] == "Success"):
                print "Editing " + title.encode('utf-8','ignore') + "...Success"
        else:
            print "Editing " + title + "...Failure"
            print self.responsebuffer.getvalue()
            exit()
            #time.sleep(.2)
    
    def apiaction(self, action):
        return self._apiurl + "?action=" + action + "&format=json"
    
    def logout(self):
        jsonr = self.httpPOST('logout',[('','')])
    
    @classmethod
    def setUpApi(cls, user, password, site, verbose=False):
        '''
        Creates a WikiApi object, log in and aquire an edit token
        '''
        #Provide url and identify (either talk-page url)
        wiki = cls('%s/w/api.php' %site,"%s/wiki/User_talk:%s" %(site, user))
        
        #Login
        wiki.login(user,password, verbose=verbose)
        #Get an edittoken
        wiki.setEditToken(verbose=verbose)
        return wiki
    
    @property
    def apiurl(self):
        return self._apiurl

class WikiDataApi(WikiApi):
    '''Extends the previous class with wikidataSpecific methods'''
    
    def getArticles(self, entities, dDict=None, site=u'svwiki', debug=False):
        '''
        Given a list of entityIds this returns their article names (at the specified site)
        :param entities: a list of entity_ids (or a single entity_id) to look at
        :param dDict: (optional) a dict object into which output is placed
        :param site: the site for which to return the sitelink
        :return: a dict with the supplied entities as keys and a each value being a dict of teh form
                 page = {
                         'title':<Article title or None if missing>,
                         'url':<Article url (without http) or None if missing>,
                         'missing':<False or True if entity is missing>,
                         'missingSite':<False or True if entity exists but does not have an article on that site>}
                If an error is encountered it returns None
        '''
        #if only one article given
        if not isinstance(entities,list):
            if (isinstance(entities,str) or isinstance(entities,unicode)):
                entities = [entities,]
            else:
                print '"getArticles" requires a list of entity_ids or a single entity_id.'
                return None
        
        #if no initial dict suplied
        if dDict is None:
            dDict ={}
        
        #do an upper limit check and split into several requests if necessary
        reqlimit = 50 #max 50 titles per request allowed
        entities = list(set(entities)) #remove dupes
        if len(entities) > reqlimit:
            i=0
            while (i+reqlimit < len(entities)):
                self.getArticles(entities[i:i+reqlimit], dDict, site=site, debug=debug)
                i=i+reqlimit
            #less than reqlimit left
            entities = entities[i:]
            if len(entities) < 1: #i.e. exactly divisible by reqlimit
                return dDict
        
        #Single run
        jsonr = self.httpPOST("wbgetentities", [('props', 'sitelinks/urls'),
                                    ('ids', '|'.join(entities).encode('utf-8'))])
        if debug:
            print u'getArticles() : site=%s ; entities=%s\n' %(site, '|'.join(entities))
            print jsonr
        
        #deal with problems
        if not jsonr['success'] == 1:
            return None
        
        #all is good
        pages = jsonr['entities'] #a dict
        for k, v in pages.iteritems():
            page = {'title':None, 'url':None, 'missing':False, 'missingSite':False}
            if 'missing' in v.keys(): #entity is missing
                page['missing'] = True
            else:
                if site in v['sitelinks'].keys():
                    page['title'] = v['sitelinks'][site]['title']
                    page['url'] = v['sitelinks'][site]['url']
                else:
                    page['missingSite'] = True  #the site is missing
            dDict[k] = page.copy()
        
        return dDict #in case one was not supplied
    
    def makeEntity(self, article, site=u'svwiki', lang=None, label=None, debug=False):
        '''
        Given an article on a certain site creates a wikidata entity for this object and returns the entity id
        :param article: the article for which to create a wikidata entity
        :param site: the site where the article exists
        :param label: (optional) a label to add
        :param lang: the language in which to add the label
        :return: the entityId of the new object
                If an error is encountered it returns None
        '''
        if not (isinstance(article,str) or isinstance(article,unicode)): #does this give trouble with utf-8 strings?
            print '"makeEntity" requires a single article name as its parameter'
            return None
        
        #if lang and label:
            #data = u'{"sitelinks":{"%s":{"site":"%s","title":"%s"}},"labels":{"%s":{"language":"%s","value":"%s"}}}' %(site, site, article, lang, lang, label)
        #else:
            #data = u'{"sitelinks":{"%s":{"site":"%s","title":"%s"}}}' %(site, site, article)
        
        if lang and label:
            data = u'{"sitelinks":[{"site":"%s","title":"%s"}],"labels":[{"language":"%s","value":"%s"}]}' %(site, article, lang, label)
        else:
            data = u'{"sitelinks":[{"site":"%s","title":"%s"}]}' %(site, article)
        
        jsonr = self.httpPOST("wbeditentity", [('new', 'item'),
                                    ('data', data.encode('utf-8')),
                                    ('token', str(self.edittoken))])
        if debug:
            print u'makeEntity() : site=%s ; article=%s\n' %(site, article)
            print jsonr
        
        #possible errors
        if u'error' in jsonr.keys():
            if (jsonr[u'error'][u'code'] == u'failed-save' and jsonr[u'error'][u'messages'][u'0'][u'name'] == u'wikibase-error-sitelink-already-used'):
                entity = jsonr[u'error'][u'messages'][u'0'][u'parameters'][2]
                print u'%s:%s already saved as %s' %(site, article, entity)
                return entity
            elif (jsonr[u'error'][u'code'] == u'no-external-page') :
                print u'%s:%s does not exist' %(site, article)
            else:
                print jsonr[u'error']
            return None
        #deal with success
        if u'success' in jsonr.keys():
            return jsonr[u'entity'][u'id']
