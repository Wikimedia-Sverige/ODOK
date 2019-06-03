#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
'''
 WikiApi
 Forked from PyCJWiki Version 1.31 (C) by Smallman12q <https://en.wikipedia.org/wiki/User_talk:Smallman12q/> GPL, see <http://www.gnu.org/licenses/>.
 Original source: <https://commons.wikimedia.org/w/index.php?title=User:Smallman12q/PyCJWiki&oldid=93284775/>
 Requires python2.7, json, and PyCurl

 TODO
   * Separate debug from verbose. There should be no non-error print statement which is not tied to either of these.
   ** Standardise verbose output to always use self.output wrapper
       (Do this also for odok.OdokApi)
   _http errors should be thrown again so that they can be caught upstream (instead of printed to commandline)
   _http timeout errors should output on verbose even if retried
   Allow setup to set Delay parameters and for these to be changed during the run
   Break out WikiDataApi, WikiCommonsApi as separate files
   consider integrating some elements of Europeana.py (e.g. getImageInfos() into WikiCommonsApi.
       Deal with encoding of filenames, proper use of ignorewarnings etc., purging (think Broken filelinks)
   Most "while 'query-continue'" could be redone as calling the same function with a 'query-continue' parameter
   Listify function (for all of the if is not a list then return a list
   Split by reqlimit function

'''

import pycurl
import json
import cStringIO
import urllib
import time
import traceback
import mmap
import sys  # consider removing


class WikiApi(object):

    class Delay:
        """
            Delay enum, the delays for requests etc.
            Delay implemented as sleep before given request...could be improved
        """
        ALLREQUESTS = 0
        UPLOAD = 0

    # useragenturl and contact in unicode
    def __init__(self, apiurl, useragentidentify, scriptidentify,
                 verbose=False):
        """
        :param apiurl: The url of the api.php such as https://commons.wikimedia.org/w/api.php
            Pass as str
        :param useragentidentify: The identification to be sent in the header.
            Such as u'https://commons.wikimedia.org/wiki/User_talk:Smallman12q'
            Part of https://www.mediawiki.org/wiki/Api#Identifying_your_client
            Pass as u
        """

        # Wiki vars
        self._apiurl = apiurl
        self.userName = None
        self.tokens = []
        self.edittoken = None
        self.reqlimit = None
        self.verbose = verbose

        # Response buffer
        self.responsebuffer = cStringIO.StringIO()
        self.headerbuffer = cStringIO.StringIO()
        self.clearresponsebufferafterresponse = False  # True will clear, and save memory, but less useful if error

        # Set up reusable curl connection
        self.sitecurl = pycurl.Curl()
        self.sitecurl.setopt(pycurl.WRITEFUNCTION, self.responsebuffer.write)  # Writes to response buffer
        self.sitecurl.setopt(pycurl.HEADERFUNCTION, self.headerbuffer.write)  # Writes to response buffer
        self.sitecurl.setopt(pycurl.COOKIEFILE, "")  # Use in-memory cookie
        self.sitecurl.setopt(pycurl.USERAGENT, scriptidentify.encode('utf-8') + ' (' + useragentidentify.encode('utf-8') + ')')
        self.sitecurl.setopt(pycurl.POST, 1)
        self.sitecurl.setopt(pycurl.CONNECTTIMEOUT, 60)
        self.sitecurl.setopt(pycurl.TIMEOUT, 120)
        self.sitecurl.setopt(pycurl.ENCODING, 'gzip, deflate')
        self.sitecurl.setopt(pycurl.HTTPHEADER, ["Expect:", "Connection: Keep-Alive", "Keep-Alive: 60"])
        # self.sitecurl.setopt(pycurl.PROXY, 'http://localhost:8888')  # Proxy if needed

    def _httpREQ(self, action, params, func, timeoutretry=0, debug=False):
        """
        A more generic version allowing either POST or GET requests
        :param action: The action, pass as str
        :param params: The params to be posted
        :param func: a function (self.httpPOST or selfhttpGET)
        :param timeoutretry: A counter for timeoutretries
        :return: json object
        """

        # Do the get/post thing
        #   self.sitecurl.setopt(pycurl.HTTPGET/POST, params)
        #   Set curl http request
        #   self.sitecurl.setopt(pycurl.URL, self.apiaction(action))

        # Clear response buffer
        self.responsebuffer.truncate(0)

        if debug:
            print self.sitecurl.getinfo(pycurl.EFFECTIVE_URL)

        # Try the curl http request
        try:
            time.sleep(self.Delay.ALLREQUESTS)
            self.sitecurl.perform()
        except pycurl.error, error:
            errno, errstr = error

            # Response Timed Out, Retry up to 3 times
            if(errno == 28):
                if(timeoutretry < 3):
                    time.sleep(2)
                    func(action, params, timeoutretry=(timeoutretry + 1))
                else:
                    print "timed out 3 times! Not retrying"
            else:
                print("An error occurred: %d:" % errno, errstr)
                traceback.print_exc()

        if debug:
            print self.responsebuffer.getvalue()
        try:
            jsonr = json.loads(self.responsebuffer.getvalue())
        except ValueError:
            print self.headerbuffer.getvalue()
            exit(1)

        if self.clearresponsebufferafterresponse:
            self.responsebuffer.truncate(0)

        self.headerbuffer.truncate(0)  # no need to keep more than the last

        # check for warnings
        if 'warnings' in jsonr.keys():
            for k, v in jsonr['warnings'].iteritems():
                print u'Warning for "%s":' % k
                for kk, vv in jsonr['warnings'][k].iteritems():
                    print u'\t"%s": %s' % (kk, vv)

        return jsonr

    def httpGET(self, action, params, timeoutretry=0, form=None, debug=False):
        """
        :param action: The action, pass as str
        :param params: The params to be gotten (in addition to action)
        :param timeoutretry: A counter for timeoutretries
        :return:
        """
        # Set curl http request
        self.sitecurl.setopt(pycurl.HTTPGET, 1)
        self.sitecurl.setopt(pycurl.URL, self.apiaction(action, form=form) +
                             '&' + urllib.urlencode(params))

        return self._httpREQ(action, params, self.httpGET, timeoutretry=timeoutretry, debug=debug)

    def httpPOST(self, action, params, timeoutretry=0, form=None, debug=False):
        """
        :param action: The action, pass as str
        :param params: The params to be posted
        :param timeoutretry: A counter for timeoutretries
        :return: json object
        """

        # Set curl http request
        self.sitecurl.setopt(pycurl.URL, self.apiaction(action, form=form))
        self.sitecurl.setopt(pycurl.HTTPPOST, params)

        return self._httpREQ(action, params, self.httpPOST, timeoutretry=timeoutretry, debug=debug)

    def httpPOSTold(self, action, params, timeoutretry=0, form=None, debug=False):
        """
        :param action: The action, pass as str
        :param params: The params to be posted
        :param timeoutretry: A counter for timeoutretries
        :return: json object
        """
        # Clear response buffer
        self.responsebuffer.truncate(0)

        # Set curl http request
        self.sitecurl.setopt(pycurl.URL, self.apiaction(action, form=form))
        self.sitecurl.setopt(pycurl.HTTPPOST, params)

        if debug:
            print self.sitecurl.getinfo(pycurl.EFFECTIVE_URL)

        # Try the curl http request
        try:
            time.sleep(self.Delay.ALLREQUESTS)
            self.sitecurl.perform()
        except pycurl.error, error:
            errno, errstr = error
            print("An error occurred: %d:" % errno, errstr)
            traceback.print_exc()

            # Response Timed Out, Retry up to 3 times
            if(errno == 28):
                if(timeoutretry < 3):
                    time.sleep(2)
                    self.httpPOST(action, params, timeoutretry=(timeoutretry + 1))

        # print self.responsebuffer.getvalue()
        jsonr = json.loads(self.responsebuffer.getvalue())

        if self.clearresponsebufferafterresponse:
            self.responsebuffer.truncate(0)

        return jsonr

    def printResponseBuffer(self):
        print self.responsebuffer.getvalue()

    # username, userpass unicode
    def login(self, userName, userPass, verbose=True):
        """
        :param userName: username as u
        :param userPass: userpassword as u. Not stored after login
        :return:
        """
        if verbose:
            print "Logging into %s as %s" % (self._apiurl, userName)
            print "Logging in...(1/2)"

        # Request login token
        lgtoken = self.setToken('login', verbose=verbose)
        if verbose:
            print "Logging in...(1/2)...Success!"

        # Login 2/2
        if verbose:
            print "Logging in...(2/2)"
        jsonr = self.httpPOST("login", [('lgname', userName.encode('utf-8')),
                                        ('lgpassword', userPass.encode('utf-8')),
                                        ('lgtoken', lgtoken)])
        if 'Success' in jsonr['login']['result']:
            if verbose:
                print "Logging in...(2/2)...Success!"

        else:
            print "Logging in...(2/2)...Failed"
            self.printResponseBuffer()
            exit()

        self.userName = userName  # Now logged in
        if verbose:
            print "You are now logged in as %s" % self.userName

    def setToken(self, token, verbose=True):
        if verbose:
            print "Retrieving token: %s" % token
        tokenkey = '%stoken' % token
        jsonr = self.httpPOST("query", [('meta', 'tokens'),
                                        ('type', str(token))])
        if (tokenkey not in jsonr['query']['tokens'].keys()) or (jsonr['query']['tokens'][tokenkey] == "+\\"):
            print "%s token not set." % token
            self.printResponseBuffer()
            exit()
        else:
            if verbose:
                print "%s token retrieved: %s" % (token, str(jsonr['query']['tokens'][tokenkey]))
            return str(jsonr['query']['tokens'][tokenkey])

    def setEditToken(self, verbose=True):
        self.edittoken = self.setToken('csrf', verbose=verbose)

    def clearEditToken(self):
        self.edittoken = None
        # TODO Clear in tokens dict when implemented

    def getTimestamp(self, article, debug=False):
        """
        Returns the timestamp of (the latest revision of) the provided article
        :parameter article: pagetitle to look at
        :return: timestamp as string in ISO 8601 format
        """
        jsonr = self.httpPOST("query", [('prop', 'revisions'),
                                        ('titles', article.encode('utf-8')),
                                        ('rvprop', 'timestamp'),
                                        ('rvlimit', '1')])
        if debug:
            print u"getTimestamp(): article=%s\n" % article
            print jsonr

        pageid = jsonr['query']['pages'].keys()[0]
        if pageid == u'-1':
            print "no entry for \"%s\"" % article
            return None
        else:
            return jsonr['query']['pages'][pageid]['revisions'][0]['timestamp']

    def getEmbeddedin(self, templatename, einamespace, debug=False):
        """
        Returns list of all pages embedding a given template
        :param templatename: The template to look for (including \"Template:\")
        :param einamespace: namespace to limit the search to (0=main)
        :return: list containing pagenames
        """

        print "Fetching pages embedding: %s" % templatename
        members = []
        # action=query&list=embeddedin&cmtitle=Template:!
        jsonr = self.httpPOST("query", [('list', 'embeddedin'),
                                        ('eititle', templatename.encode('utf-8')),
                                        ('einamespace', str(einamespace)),
                                        ('rawcontinue', ''),
                                        ('eilimit', '500')])
        if debug:
            print u"getEmbeddedin(): templatename=%s\n" % templatename
            print jsonr

        # {"query":{"embeddedin":[{"pageid":5,"ns":0,"title":"Abbek\u00e5s"}]},"query-continue":{"embeddedin":{"eicontinue":"10|!|65"}}}
        for page in jsonr['query']['embeddedin']:
            members.append((page['title']))

        while 'query-continue' in jsonr:
            print "Fetching pages embeding: %s...fetching more" % templatename
            # print jsonr['query-continue']['embeddedin']['eicontinue']
            jsonr = self.httpPOST("query", [('list', 'embeddedin'),
                                            ('eititle', templatename.encode('utf-8')),
                                            ('eilimit', '500'),
                                            ('einamespace', str(einamespace)),
                                            ('rawcontinue', ''),
                                            ('eicontinue', str(jsonr['query-continue']['embeddedin']['eicontinue']))])
            for page in jsonr['query']['embeddedin']:
                members.append((page['title']))

        print "Fetching pages embedding: %s...complete" % templatename
        return members

    def getEmbeddedinTimestamps(self, templatename, einamespace, debug=False):
        """
        Returns a list of all pages embedding a given template along with the timestamp for when it was last edited
        combines getEmbeddedin() and getTimestamps()
        :param templatename: The template to look for (including \"Template:\")
        :param einamespace: namespace to limit the search to (0=main)
        :return: list containing dicts {pagename, timestamp} where timestamp is a string in ISO 8601 format
        """

        print "Fetching pages embedding: %s" % templatename
        members = []
        # action=query&prop=revisions&format=json&rvprop=timestamp&generator=embeddedin&geititle=Mall%3A!&geinamespace=0&geilimit=500
        jsonr = self.httpPOST("query", [('prop', 'revisions'),
                                        ('rvprop', 'timestamp'),
                                        ('generator', 'embeddedin'),
                                        ('geititle', templatename.encode('utf-8')),
                                        ('geinamespace', str(einamespace)),
                                        ('rawcontinue', ''),
                                        ('geilimit', '500')])
        if debug:
            print u"getEmbeddedinTimestamps() templatename:%s \n" % templatename
            print jsonr

        # {"query-continue":{"embeddedin":{"geicontinue":"10|Offentligkonstlista|1723456"}},"query":{"pages":{"1718037":{"pageid":1718037,"ns":0,"title":"Lista...","revisions":[{"timestamp":"2013-08-24T13:01:49Z"}]}}}}
        for page in jsonr['query']['pages']:
            page = jsonr['query']['pages'][page]
            members.append({'title': page['title'], 'timestamp': page['revisions'][0]['timestamp']})

        while 'query-continue' in jsonr:
            print "Fetching pages embedding: %s...fetching more" % templatename
            # print jsonr['query-continue']['embeddedin']['geicontinue']
            jsonr = self.httpPOST("query", [
                ('prop', 'revisions'),
                ('rvprop', 'timestamp'),
                ('generator', 'embeddedin'),
                ('geititle', templatename.encode('utf-8')),
                ('geinamespace', str(einamespace)),
                ('rawcontinue', ''),
                ('geilimit', '500'),
                ('geicontinue', str(jsonr['query-continue']['embeddedin']['geicontinue']))])
            for page in jsonr['query']['pages']:
                page = jsonr['query']['pages'][page]
                members.append({'title': page['title'], 'timestamp': page['revisions'][0]['timestamp']})

        print "Fetching pages embedding: %s...complete" % templatename
        return members

    def getCategoryMembers(self, categoryname, cmnamespace, debug=False):
        """
        Returns a list of all pages in a given category (and namespace)
        :param categoryname: The category to look in (including \"Category:\")
        :param cmnamespace: namespace to limit the search to (0=main)
        :return: list of pagenames
        """
        print "Fetching categorymembers: %s" % categoryname
        members = []
        # action=query&list=categorymembers&cmtitle=Category:Physics
        jsonr = self.httpPOST("query", [('list', 'categorymembers'),
                                        ('cmtitle', categoryname.encode('utf-8')),
                                        ('cmnamespace', str(cmnamespace)),
                                        ('rawcontinue', ''),
                                        ('cmlimit', '500')])
        if debug:
            print u"getCategoryMembers() categoryname:%s \n" % categoryname
            print jsonr

        # {"query":{"categorymembers":[{"pageid":22688097,"ns":0,"title":"Branches of physics"}]},"query-continue":{"categorymembers":{"cmcontinue":"page|200a474c4f5353415259204f4620434c4153534943414c2050485953494353|3445246"}}}
        for page in jsonr['query']['categorymembers']:
            members.append((page['title']))

        while 'query-continue' in jsonr:
            print "Fetching categorymembers: %s...fetching more" % categoryname
            # print jsonr['query-continue']['categorymembers']['cmcontinue']
            jsonr = self.httpPOST("query", [
                ('list', 'categorymembers'),
                ('cmtitle', categoryname.encode('utf-8')),
                ('cmnamespace', str(cmnamespace)),
                ('rawcontinue', ''),
                ('cmlimit', '500'),
                ('cmcontinue', str(jsonr['query-continue']['categorymembers']['cmcontinue']))])
            for page in jsonr['query']['categorymembers']:
                members.append((page['title']))

        print "Fetching categorymembers: %s...complete" % categoryname
        return members

    def getImageUsage(self, filename, iunamespace=None, debug=False):
        """
        Returns a list of all pages using a given image
        :param filename: The file to look for (including \"File:\")
        :param iunamespace: namespace to limit the search to (0=main, 6=file)
        :return: list of pagenames
        """
        # print "Fetching imageusages: " + filename
        members = []
        # action=query&list=imageusage&iutitle=File:Foo.jpg
        requestparams = [('list', 'imageusage'),
                         ('iutitle', filename.encode('utf-8')),
                         ('rawcontinue', ''),
                         ('iulimit', '500')]
        if iunamespace:
            requestparams.append(('iunamespace', str(iunamespace)))
        jsonr = self.httpPOST("query", requestparams)

        if debug:
            print u"getImageUsage() filename:%s \n" % filename
            print jsonr

        # {"query":{"imageusage":[{"pageid":7839165,"ns":2,"title":"User:Duesentrieb/ImageRenderBug"},{"query-continue":{"imageusage":{"iucontinue":"6|Wikimedia_Sverige_logo.svg|12128338"}}
        for page in jsonr['query']['imageusage']:
            members.append((page['title']))

        while 'query-continue' in jsonr:
            # print  "Fetching imageusages: %s...fetching more" % filename
            # print jsonr['query-continue']['imageusage']['iucontinue']
            requestparams.append(('iucontinue', str(jsonr['query-continue']['imageusage']['iucontinue'])))
            jsonr = self.httpPOST("query", requestparams)

            for page in jsonr['query']['imageusage']:
                members.append((page['title']))

        # print  "Fetching imageusages: %s...complete" % filename
        return members

    def getImages(self, articles, results=None, offset=None, debug=False):
        """
        Return all of the images used in the given page
        :param articles: a list of pagenames (or a single pagename) to look at
        :param results: a list to which filenames should be added
        :param offset: the imcontinue parameter
        :return: list of filenames (without prefix)
        """
        # if only one article given
        if not isinstance(articles, list):
            if isinstance(articles, (str, unicode)):
                articles = [articles, ]
            else:
                print "getImages() requires a list of pagenames or a single pagename."
                return None

        # if no initial list supplied
        if results is None:
            results = []

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.reqlimit  # max 50 titles per request allowed
        if len(articles) > reqlimit:
            i = 0
            while (i + reqlimit < len(articles)):
                results = self.getImages(articles[i:i + reqlimit],
                                         results=results,
                                         offset=offset, debug=debug)
                i += reqlimit
            # less than reqlimit left
            articles = articles[i:]
            if len(articles) < 1:  # i.e. exactly divisible by reqlimit
                return results

        # do a single request
        requestparams = [
            ('prop', 'images'),
            ('imlimit', '100'),
            ('rawcontinue', ''),
            ('titles', u'|'.join(articles).encode('utf-8'))]
        if offset:
            requestparams.append(('imcontinue', offset.encode('utf-8')))
        jsonr = self.httpPOST("query", requestparams)
        if debug:
            print u"getImages(): articles=%s\n" % '|'.join(articles)
            print jsonr

        # parse results
        for page, info in jsonr['query']['pages'].iteritems():
            if 'images' in info.keys():
                for image in info['images']:
                    results.append(image['title'].split(':')[-1])

        # handle query-continue
        if 'query-continue' in jsonr.keys():
            offset = jsonr['query-continue']['images']['imcontinue']
            results = self.getImages(articles, results=results,
                                     offset=offset, debug=debug)

        return results

    def getPageInfo(self, articles, dDict=None, debug=False):
        """
        Given a list of articles this tells us if the page is either
        * Non-existent (red link)
        * A redirect (and returns real page)
        * A disambiguation page
        * Normal page
        and whether the page corresponds to a wikidata entry (and returns the wikidata id)
        :param articles: a list of pagenames (or a single pagename) to look at
        :param dDict: (optional) a dict object into which output is placed
        :return: a dict with the supplied pagenames as keys and a each value
        being a dict of corresponding properties with possible parameters being:
        redirected, missing, disambiguation, wikidata
        """
        # if only one article given
        if not isinstance(articles, list):
            if isinstance(articles, (str, unicode)):
                articles = [articles, ]
            else:
                print "getPageInfo() requires a list of pagenames or a single pagename."
                return None

        # if no initial dict supplied
        if dDict is None:
            dDict = {}

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.reqlimit  # max 50 titles per request allowed
        articles = list(set(articles))  # remove dupes
        if len(articles) > reqlimit:
            i = 0
            while (i + reqlimit < len(articles)):
                self.getPageInfo(articles[i:i + reqlimit], dDict, debug=debug)
                i += reqlimit
            # less than reqlimit left
            articles = articles[i:]
            if len(articles) < 1:  # i.e. exactly divisible by reqlimit
                return dDict

        # Single run
        jsonr = self.httpPOST("query", [
            ('prop', 'pageprops'),
            ('redirects', ''),
            ('titles', '|'.join(articles).encode('utf-8'))])
        if debug:
            print u"getPageInfo(): articles=%s\n" % '|'.join(articles)
            print jsonr

        # start with redirects
        rDict = {}
        if 'redirects' in jsonr['query'].keys():
            redirects = jsonr['query']['redirects']  # a list
            for r in redirects:
                if r['to'] in rDict.keys():
                    rDict[r['to']].append(r['from'])
                else:
                    rDict[r['to']] = [r['from'], ]

        # then pages
        pages = jsonr['query']['pages']  # a dict
        for k, v in pages.iteritems():
            page = {}
            title = v['title']
            # missing
            if 'missing' in v.keys():
                page['missing'] = True
            # properties
            if 'pageprops' in v.keys():
                u = v['pageprops']
                if 'disambiguation' in u.keys():
                    page['disambiguation'] = True
                if 'wikibase_item' in u.keys():
                    page['wikidata'] = u['wikibase_item'].upper()
            # check if redirected
            if title in rDict.keys():
                if title in articles:  # need to make sure search didn't look for both redirecting and real title
                    dDict[title] = page.copy()
                page['redirect'] = title
                for r in rDict[title]:
                    title = r
                    dDict[title] = page.copy()
            else:
                dDict[title] = page.copy()

        return dDict  # in case one was not supplied

    def getPage(self, articles, dDict=None, debug=False):
        """
        Given an article this returns the contents of (the latest revision of) the page
        :param articles: a list of pagenames (or a single pagename) to look at
        :param dDict: (optional) a dict object into which output is placed
        :return: dict of contents with pagenames as key
        """
        # if only one article given
        if not isinstance(articles, list):
            if isinstance(articles, (str, unicode)):
                articles = [articles, ]
            else:
                print "getPage() requires a list of pagenames or a single pagename."
                return None

        # if no initial dict supplied
        if dDict is None:
            dDict = {}

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.reqlimit  # max 50 titles per request allowed
        articles = list(set(articles))  # remove dupes
        if len(articles) > reqlimit:
            i = 0
            while (i + reqlimit < len(articles)):
                self.getPage(articles[i:i + reqlimit], dDict, debug=debug)
                i += reqlimit
            # less than reqlimit left
            articles = articles[i:]
            if len(articles) < 1:  # i.e. exactly divisible by reqlimit
                return dDict

        # Single run
        jsonr = self.httpPOST("query", [
            ('prop', 'revisions'),
            ('rvprop', 'content'),
            ('titles', '|'.join(articles).encode('utf-8'))])
        if debug:
            print u"getPage() : articles= %s\n" % '|'.join(articles)
            print jsonr

        for page in jsonr['query']['pages']:
            if int(page) < 0:  # Either missing or invalid
                dDict[jsonr['query']['pages'][page]['title']] = None
            else:
                dDict[jsonr['query']['pages'][page]['title']] = jsonr['query']['pages'][page]['revisions'][0]['*']

        return dDict  # in case one was not supplied

    def getContributions(self, article, dDict=None, start=None, end=None, debug=False):
        """
        Given an article this returns the contributions to that page
        :param article: a single pagename to look at
        :param dDict: (optional) a dict object into which output is placed
        :param start: (optional) a date from which to start enumerating
        :param end: (optional) a date from which to start enumerating
            start and end should be iso date strings of the form YYYY-MM-DD
        :return: dict of
            users:
                _anon: list_of_anon_ips
                username: number of edits
            size:
                absolute: sum of absolute change of bytes
                relative: sum of relative change of bytes
        :return: None on fail or no revisions
        """
        # if only one article given
        if not isinstance(article, (str, unicode)):
            print "getContributors() requires a single pagename."
            return None

        # if no initial dict supplied
        if dDict is None:
            dDict = {
                'users': {
                    '_anon': []
                },
                'size': {
                    'absolute': 0,
                    'relative': 0
                }
            }

        # handle parameters
        requestparams = [('prop', 'revisions'),
                         ('rvprop', 'ids|user|size'),
                         ('rvlimit', '500'),
                         ('rvdir', 'newer'),
                         ('rawcontinue', ''),
                         ('titles', article.encode('utf-8'))]
        if start is not None:
            requestparams.append(('rvstart', '%sT00:00:00Z' % start))
        if end is not None:
            requestparams.append(('rvend', '%sT00:00:00Z' % end))

        # First run
        jsonr = self.httpPOST("query", requestparams)
        if debug:
            print u"getContributors() : article = %s\n" % article
            print jsonr

        pageid = jsonr['query']['pages'].keys()[0]
        if int(pageid) < 0:  # Either missing or invalid
            print "getContributors(): %s was not a valid page" % article
            return None

        # check if any revisions
        if 'revisions' not in jsonr['query']['pages'][pageid].keys():
            return None

        # store all revisions
        revs = []
        revs += jsonr['query']['pages'][pageid]['revisions']

        # get any remaining
        while 'query-continue' in jsonr:
            rvcontinue = str(jsonr['query-continue']['revisions']['rvcontinue'])
            jsonr = self.httpPOST("query", requestparams + [('rvcontinue', rvcontinue)])
            # same pageid since only looking at one article
            revs += jsonr['query']['pages'][pageid]['revisions']

        # analyse revisions
        prev_size = None
        for rev in revs:
            # handle user info
            if 'anon' in rev.keys():
                dDict['users']['_anon'].append(rev['user'])
            else:
                if rev['user'] in dDict['users'].keys():
                    dDict['users'][rev['user']] += 1
                else:
                    dDict['users'][rev['user']] = 1

            # handle first revision
            if prev_size is None:
                if rev['parentid'] == 0:  # article created
                    prev_size = 0
                else:
                    prev_size = rev['size']  # essentially don't count this one

            # handle size info
            size_diff = rev['size'] - prev_size
            dDict['size']['relative'] += size_diff
            dDict['size']['absolute'] += abs(size_diff)
            prev_size = rev['size']

        # filter out non-unique anons
        dDict['users']['_anon'] = list(set(dDict['users']['_anon']))

        return dDict

    def editText(self, title, newtext, comment, minor=False, bot=True, userassert='bot', nocreate=False, debug=False, append=False):
        print "Editing %s" % title.encode('utf-8', 'ignore')
        requestparams = [('title', title.encode('utf-8')),
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
            requestparams.append(('nocreate', 'true'))
        if append:
            requestparams.append(('appendtext', newtext.encode('utf-8')))

        jsonr = self.httpPOST("edit", requestparams)
        if debug:
            print u"editText(): title=%s\n" % title
            print jsonr

        if ('edit' in jsonr) and (jsonr['edit']['result'] == "Success"):
            print "Editing %s...Success" % title.encode('utf-8', 'ignore')
        else:
            print "Editing %s...Failure" % title
            print self.responsebuffer.getvalue()
            exit()
            # time.sleep(.2)

    def getUserData(self, users, dDict=None, debug=False):
        """
        Returns some basic (public) information about a set of users
        :param users: a list of usernames (or a single username) to look at
        :param dDict: (optional) a dict object into which output is placed
        :return: dict of contents with usernames as key
        """
        # if only one article given
        if not isinstance(users, list):
            if isinstance(users, (str, unicode)):
                users = [users, ]
            else:
                print "getUserData() requires a single or list of usernames."
                return None

        # if no initial dict supplied
        if dDict is None:
            dDict = {}

        # do an upper limit check and split into several requests if necessary
        users = list(set(users))  # remove dupes
        if len(users) > self.reqlimit:
            i = 0
            while (i + self.reqlimit < len(users)):
                self.getUserData(users[i:i + self.reqlimit],
                                 dDict=dDict,
                                 debug=debug)
                i += self.reqlimit
            # less than reqlimit left
            users = users[i:]
            if len(users) < 1:  # i.e. exactly divisible by reqlimit
                return dDict

        # Single run
        jsonr = self.httpPOST("query", [('list', 'users'),
                                        ('usprop', 'editcount|registration|emailable|gender'),
                                        ('ususers', '|'.join(users).encode('utf-8'))])

        if debug:
            print u"getUserData() : users= %s\n" % '|'.join(users)
            print jsonr

        # parse replies
        for user in jsonr['query']['users']:
            if 'missing' in user.keys() or 'invalid' in user.keys():
                dDict[user['name']] = {'reg': '-',
                                       'edits': '-',
                                       'gender': '-',
                                       'emailable': '-'}
                continue
            dDict[user['name']] = {'reg': user['registration'],
                                   'edits': user['editcount'],
                                   'gender': user['gender'],
                                   'emailable': False}
            if 'emailable' in user.keys():
                dDict[user['name']]['emailable'] = True
            # remove timestamp
            if user['registration']:  # this can be null
                dDict[user['name']]['reg'] = user['registration'][:10]

        return dDict

    def getPageCategories(self, articles, nohidden=False, dDict=None, debug=False):
        """
        Returns the articles of a pageGiven an article this returns the contents of (the latest revision of) the page
        :param articles: a list of pagenames (or a single pagename) to look at
        :param dDict: (optional) a dict object into which output is placed
        :return: dict of contents with pagenames as key pagename:listofCategories
        """
        # if only one article given
        if not isinstance(articles, list):
            if isinstance(articles, (str, unicode)):
                articles = [articles, ]
            else:
                print "getPageCategories() requires a list of pagenames or a single pagename."
                return None

        # if no initial dict supplied
        if dDict is None:
            dDict = {}

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.reqlimit  # max 50 titles per request allowed
        articles = list(set(articles))  # remove dupes
        if len(articles) > reqlimit:
            i = 0
            while (i + reqlimit < len(articles)):
                self.getPageCategories(articles[i:i + reqlimit], nohidden=nohidden,
                                       dDict=dDict, debug=debug)
                i += reqlimit
            # less than reqlimit left
            articles = articles[i:]
            if len(articles) < 1:  # i.e. exactly divisible by reqlimit
                return dDict

        # Single run
        # %s?action=query&prop=categories&format=json&clshow=!hidden&titles=
        if nohidden:
            clshow = '!hidden'
        else:
            clshow = ''
        jsonr = self.httpPOST("query", [('prop', 'categories'),
                                        ('cllimit', '500'),
                                        ('clshow', clshow),
                                        ('rawcontinue', ''),
                                        ('titles', '|'.join(articles).encode('utf-8'))])

        if debug:
            print u"getPageCategories() : articles= %s\n" % '|'.join(articles)
            print jsonr

        # {"query":{"pages":{"497":{"pageid":497,"ns":0,"title":"Edvin \u00d6hrstr\u00f6m","categories":[{"ns":14,"title":"Kategori:Avlidna 1994"},{"ns":14,"title":"Kategori:F\u00f6dda 1906"}]}}}}
        for page in jsonr['query']['pages']:
            page = jsonr['query']['pages'][page]

            # find cats
            categories = []
            if 'categories' not in page.keys():  # if page is missing or has no categories
                categories = None
            else:
                for cat in page['categories']:
                    categories.append(cat['title'])
            # stash
            title = page['title']
            if title in dDict.keys():  # since clcontinue may split categories into two batches
                dDict[title] += categories
            else:
                dDict[title] = categories

        while 'query-continue' in jsonr:
            # print  "Fetching pagecategories: %s...fetching more" % '|'.join(articles)
            # print jsonr['query-continue']['categorymembers']['clcontinue']
            jsonr = self.httpPOST("query", [
                ('prop', 'categories'),
                ('cllimit', '500'),
                ('clshow', clshow),
                ('rawcontinue', ''),
                ('titles', '|'.join(articles).encode('utf-8'))
                ('clcontinue', str(jsonr['query-continue']['categories']['clcontinue']))])

            for page in jsonr['query']['pages']:
                page = jsonr['query']['pages'][page]

                # find cats
                categories = []
                if 'categories' not in page.keys():  # if page is missing or has no categories
                    categories = None
                else:
                    for cat in page['categories']:
                        categories.append(cat['title'])
                # stash
                title = page['title']
                if title in dDict.keys():  # since clcontinue may split categories into two batches
                    dDict[title] += categories
                else:
                    dDict[title] = categories

        # print  "Fetching pagecategories: %s...complete" % '|'.join(articles)
        return dDict  # in case one was not supplied

    def apiaction(self, action, form=None):
        if not form:
            return self._apiurl + "?action=" + action + "&format=json"
        else:
            return self._apiurl + "?action=" + action + "&format=" + form

    def logout(self):
        self.httpPOST('logout', [('token', str(self.edittoken))])

    def output(self, text):
        """
        A wrapper to only print text if verbose is True
        :param text: text to print
        :return: None
        """
        if self.verbose:
            print text

    def limitByBytes(self, valList, reqlimit=None):
        """
        php $_GET is limited to 512 bytes per request and parameter
        This function therefore provides a way of limiting the number
        of values further than reqlimit to respect this limitation.
        :param valList: a list of values to be compressed into one parameter
        :param reqlimit: (optional) the number of values to send in each request
        :return: a new reqlimit
        """
        byteLimit = 512.0
        if reqlimit is None:
            reqlimit = len(valList)
        oldresult = reqlimit
        while True:
            byteLength = len('|'.join(valList[:reqlimit]).encode('utf-8'))
            num = byteLength / byteLimit
            if not num > 1:
                break
            reqlimit = int(reqlimit / num)
            if reqlimit < 1:
                print "%r byte limit broken by a single parameter! What to do?" % int(byteLimit)
                return None  # Should do proper error handling
            # prevent infinite loop
            if reqlimit == oldresult:
                print "limitByBytes() in a loop with b/n/r = %r/%f/%r" % (byteLength, num, reqlimit)
                if reqlimit > 1:
                    reqlimit = reqlimit - 1
                break
            else:
                oldresult = reqlimit
        return reqlimit

    @classmethod
    def setUpApi(cls, user, password, site, reqlimit=50, verbose=False, separator='w', scriptidentify=u'OdokBot/0.5'):
        """
        Creates a WikiApi object, log in and aquire an edit token
        """
        # Provide url and identify (either talk-page url)
        wiki = cls('%s/%s/api.php' % (site, separator), "%s/wiki/User_talk:%s" % (site, user), scriptidentify, verbose)

        # Set reqlimit for wp.apis
        wiki.reqlimit = reqlimit

        # Login
        wiki.login(user, password, verbose=verbose)
        # Get an edittoken
        wiki.setEditToken(verbose=verbose)
        return wiki

    @property
    def apiurl(self):
        return self._apiurl


class WikiDataApi(WikiApi):
    """
    Extends the WikiApi class with Wikidata specific methods
    """

    def getArticles(self, entities, dDict=None, site=u'svwiki', debug=False):
        """
        Given a list of entityIds this returns their article names (at the specified site)
        :param entities: a list of entity_ids (or a single entity_id) to look at
        :param dDict: (optional) a dict object into which output is placed
        :param site: the site for which to return the sitelink
        :return: a dict with the supplied entities as keys and a each value being a dict of the form
                 page = {
                         'title':<Article title or None if missing>,
                         'url':<Article url (without http) or None if missing>,
                         'missing':<False or True if entity is missing>,
                         'missingSite':<False or True if entity exists but does not have an article on that site>}
                If an error is encountered it returns None
        """
        # if only one article given
        if not isinstance(entities, list):
            if isinstance(entities, (str, unicode)):
                entities = [entities, ]
            else:
                print "getArticles() requires a list of entity_ids or a single entity_id."
                return None

        # if no initial dict suplied
        if dDict is None:
            dDict = {}

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.reqlimit  # max 50 titles per request allowed
        entities = list(set(entities))  # remove dupes
        if len(entities) > reqlimit:
            i = 0
            while (i + reqlimit < len(entities)):
                self.getArticles(entities[i:i + reqlimit], dDict, site=site, debug=debug)
                i += reqlimit
            # less than reqlimit left
            entities = entities[i:]
            if len(entities) < 1:  # i.e. exactly divisible by reqlimit
                return dDict

        # Single run
        jsonr = self.httpPOST("wbgetentities", [
            ('props', 'sitelinks/urls'),
            ('ids', '|'.join(entities).encode('utf-8'))])
        if debug:
            print u"getArticles() : site=%s ; entities=%s\n" % (site, '|'.join(entities))
            print jsonr

        # deal with problems
        if not jsonr['success'] == 1:
            return None

        # all is good
        pages = jsonr['entities']  # a dict
        for k, v in pages.iteritems():
            page = {'title': None, 'url': None, 'missing': False, 'missingSite': False}
            if 'missing' in v.keys():  # entity is missing
                page['missing'] = True
            else:
                if 'sitelinks' in v.keys() and site in v['sitelinks'].keys():
                    page['title'] = v['sitelinks'][site]['title']
                    page['url'] = v['sitelinks'][site]['url']
                else:
                    page['missingSite'] = True  # the site is missing
            dDict[k] = page.copy()

        return dDict  # in case one was not supplied

    def makeEntity(self, article, site=u'svwiki', lang=None, label=None, claims=None, debug=False):
        """
        Given an article on a certain site creates a Wikidata entity for this object and returns the entity id
        :param article: the article for which to create a Wikidata entity
        :param site: the site where the article exists
        :param label: (optional) a label to add
        :param lang: the language in which to add the label
        :param claims: an array of entity claims in the form {'P#':'Q#'}
        :return: the entityId of the new object
                If an error is encountered it returns None
        """
        if not isinstance(article, (str, unicode)):  # does this give trouble with utf-8 strings?
            print "makeEntity() requires a single article name as its parameter"
            return None
        if not article or len(article.strip()) == 0:
            print "makeEntity() does not allow an empty parameter"
            return None

        # Construct the data object and convert to json
        data = {'sitelinks': [{'site': site, 'title': article}]}
        if lang and label:
            data['labels'] = [{'language': lang, 'value': label}]
        if claims:
            data['claims'] = []
            for P, Q in claims.iteritems():
                Q = int(Q[1:])
                data['claims'].append({
                    'mainsnak': {
                        'snaktype': 'value',
                        'property': P,
                        'datavalue': {
                            'value': {
                                'entity-type': 'item',
                                'numeric-id': Q},
                            'type': 'wikibase-entityid'}},
                    'type': 'statement',
                    'rank': 'normal'})
        data = json.dumps(data)  # should this be ensure_ascii=False ?

        jsonr = self.httpPOST("wbeditentity", [
            ('new', 'item'),
            ('data', data.encode('utf-8')),
            ('token', str(self.edittoken))])
        if debug:
            print u"makeEntity() : site=%s ; article=%s\n" % (site, article)
            print jsonr

        # possible errors
        if u'error' in jsonr.keys():
            if (jsonr[u'error'][u'code'] == u'failed-save' and jsonr[u'error'][u'messages'][u'0'][u'name'] == u'wikibase-error-sitelink-already-used'):
                entity = jsonr[u'error'][u'messages'][u'0'][u'parameters'][2]
                print u"%s:%s already saved as %s" % (site, article, entity)
                return entity
            elif (jsonr[u'error'][u'code'] == u'no-external-page'):
                print u"%s:%s does not exist" % (site, article)
            else:
                print jsonr[u'error']
            return None
        # deal with success
        if u'success' in jsonr.keys():
            return jsonr[u'entity'][u'id']


class CommonsApi(WikiApi):
    """
    Extends the WikiApi class with Commons specific methods
    """

    def getImageInfo(self, images, dDict=None, debug=False):
        """
        Return all of timstamp+uploader for a list of images
        :param images: a list of filenames (or a single pagename) without prefix
        :param dDict: a dict to which filenames should be added
        :param offset: the continue parameter
        :return: dict
        """
        if not isinstance(images, list):
            if isinstance(images, (str, unicode)):
                images = [images, ]
            else:
                print "getImageInfo() requires a list of filenames or a single filename."
                return None

        # if no initial dict supplied
        if dDict is None:
            dDict = {}

        # do an upper limit check and split into several requests if necessary
        reqlimit = self.reqlimit  # max 50 titles per request allowed
        if len(images) > reqlimit:
            i = 0
            while (i + reqlimit < len(images)):
                self.getImageInfo(images[i:i + reqlimit], dDict=dDict, debug=debug)
                i += reqlimit
            # less than reqlimit left
            images = images[i:]
            if len(images) < 1:  # i.e. exactly divisible by reqlimit
                return dDict

        # do a single request
        requestparams = [
            ('prop', 'imageinfo'),
            ('iiprop', 'timestamp|user'),
            ('iilimit', '1'),
            ('rawcontinue', ''),
            ('titles', 'File:' + u'|File:'.join(images).encode('utf-8'))]
        jsonr = self.httpPOST("query", requestparams)
        if debug:
            print u"getImageInfo(): images=%s\n" % '|'.join(images)
            print jsonr

        # parse results
        for page, info in jsonr['query']['pages'].iteritems():
            dDict[info['title']] = info['imageinfo'][0]

        return dDict

    # http://www.mediawiki.org/wiki/API:Upload
    def chunkupload(self, title, file, text, comment, chunksize=5,
                    chunkinmem=True, overwritepageexists=False,
                    uploadifduplicate=False, uploadifbadprefix=False,
                    ignorewarnings=False):
        """

        :param title:  File title to upload to without the "File:" in u
        :param file: The name of the file on the harddrive in str,
                     may include relative/full path
        :param text: Text in file description in u
        :param comment: The comment in u
        :param chunksize: The chunk size to upload in MB
        :param chunkinmem: Whether to read full file to memory first,
                           or read pieces off disc. True for full in mem
        :param overwritepageexists: Set to True to overwrite existing pages
        :param uploadifduplicate: Set to True to upload even if duplicate
        :param uploadifbadprefix: Set to True to upload even if bad prefix
        :param ignorewarnings: Set to True to ignore all warnings
                               (stash and upload) use with care
        :return:
        """
        txt = ''
        txt += "Chunk uploading to " + title.encode('utf-8', 'ignore')

        # collect allowed warnings
        allowedWarnings = []
        if uploadifduplicate:
            allowedWarnings.append('duplicate')
        if overwritepageexists:
            allowedWarnings.append('page-exists')
        if uploadifbadprefix:
            allowedWarnings.append('bad-prefix')
        allowedWarnings = tuple(allowedWarnings)

        # stash
        filekey, errors = self.stash(title, file, allowedWarnings,
                                     chunksize, chunkinmem, ignorewarnings)

        if errors is not None:
            txt += " " + "Upload failed"
            self.output(txt)
            txt += " " + errors
            return txt

        requestparams = [('filename', title.encode('utf-8')),
                         ('filekey', str(filekey)),
                         ('comment', comment.encode('utf-8')),
                         ('text', text.encode('utf-8')),
                         ('token', self.edittoken)]
        if ignorewarnings:
            requestparams.append(('ignorewarnings', '1'))
        jsonr = self.httpPOST("upload", requestparams)

        if 'upload' in jsonr:
            if(jsonr['upload']['result'] == "Success"):
                txt += " " + "Upload success"
            elif(jsonr['upload']['result'] == "Warning"):
                warnings = jsonr['upload']['warnings'].keys()
                if all(warning in allowedWarnings for warning in warnings):
                    filekey = jsonr['upload']['filekey']
                    jsonr = self.uploadignorewarnings(title, filekey,
                                                      text, comment)
                    if(jsonr['upload']['result'] == "Success"):
                        txt += " " + "Upload success"
                else:
                    txt += " " + "Upload warning"

        self.output(txt)
        txt += " " + self.responsebuffer.getvalue()
        return txt

    def stash(self, title, filename, allowedWarnings=(), chunksize=5,
              chunkinmem=True, ignorewarnings=False):
        """

        :param title: The filename to stash it under in u
        :param filename: The name of the file on the harddrive in str,
                         may include relative/full path
        :param allowedWarnings: Tuple of warning strings which are permitted
        :param chunksize: The chunksize in MB
        :param chunkinmem: Whether to read full file to memory first,
                           or read pieces off disc. True for full in mem
        :param ignorewarnings: Whether all warnings should be ignored
        :return (filekey, errors)
        """
        self.output("Stashing to " + title.encode('utf-8', 'ignore'))

        b = open(filename, 'r+b')
        if chunkinmem:
            # Load whole file into memory
            map = mmap.mmap(fileno=b.fileno(), length=0, access=mmap.ACCESS_COPY)
            b.close()

        else:
            map = mmap.mmap(fileno=b.fileno(), length=0, access=mmap.ACCESS_READ)
            # Close later

        requestparams = [('stash', '1'),
                         ('token', str(self.edittoken)),
                         ('filename', title.encode('utf-8')),
                         ('offset', str(map.tell())),
                         ('filesize', str(map.size())),
                         ('chunk"; filename="something', (pycurl.FORM_CONTENTTYPE, "application/octet-stream",
                                                          pycurl.FORM_CONTENTS, map.read(chunksize * 1048576)))]
        if ignorewarnings:
            requestparams.append(('ignorewarnings', '1'))
        jsonr = self.httpPOST("upload", requestparams)

        if 'upload' in jsonr:
            # @todo redo as a second call

            # handle some known warnings
            if jsonr['upload']['result'] == "Warning":
                warnings = jsonr['upload']['warnings'].keys()
                if all(warning in allowedWarnings for warning in warnings):
                    self.output("Ok warning (%s)... trying again" %
                                ", ".join(warnings))
                    return self.stash(title, filename,
                                      allowedWarnings=allowedWarnings,
                                      chunksize=chunksize,
                                      chunkinmem=chunkinmem,
                                      ignorewarnings=True)
            uploadcounter = 1
            try:
                while(jsonr['upload']['result'] == "Continue"):
                    if self.verbose:
                        sys.stdout.write('.')
                        sys.stdout.flush()

                    requestparams = [('stash', '1'),
                                     ('token', str(self.edittoken)),
                                     ('filename', title.encode('utf-8')),
                                     ('offset', str(map.tell())),
                                     ('filesize', str(map.size())),
                                     ('filekey', str(jsonr['upload']['filekey'])),
                                     ('chunk"; filename="something', (pycurl.FORM_CONTENTTYPE, "application/octet-stream",
                                                                      pycurl.FORM_CONTENTS, map.read(chunksize * 1048576)))]
                    if ignorewarnings:
                        requestparams.append(('ignorewarnings', '1'))
                    jsonr = self.httpPOST("upload", requestparams)

                    # Bug 44923
                    if((uploadcounter == 1) and (map.tell() == map.size())):
                        if(jsonr['upload']['result'] == "Continue"):
                            jsonr['upload']['result'] = "Success"
                            break
                if(jsonr['upload']['result'] == "Success"):
                    self.output('\nSuccessfully stashed at: %s' %
                                jsonr['upload']['filekey'])
                    return jsonr['upload']['filekey'], None
            except KeyError:
                print jsonr

        if not chunkinmem:
            b.close()

        # getting here meant something went wrong
        return None, self.responsebuffer.getvalue()

    def uploadignorewarnings(self, title, filekey, text, comment):
        """
        Chunkupload() but for when the file is already stashed and with
        ignorewarnings always true
        :param title: File title to upload to without the "File:" in u
        :param filekey: The filekey returned during stash
        :param text: Text in file description in u
        :param comment: The comment in u
        :return:
        """
        requestparams = [('filename', title.encode('utf-8')),
                         ('filekey', str(filekey)),
                         ('comment', comment.encode('utf-8')),
                         ('text', text.encode('utf-8')),
                         ('token', self.edittoken),
                         ('ignorewarnings', '1')]
        jsonr = self.httpPOST("upload", requestparams)
        return jsonr
