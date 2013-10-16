# -*- coding: UTF-8  -*-
#
# Methods comonly shared by the tool scripts
#
import codecs
import os
import operator
import urllib, urllib2
from json import loads

def openFile(filename):
    '''opens a given file (utf-8) and returns the lines'''
    fin = codecs.open(filename, 'r', 'utf8')
    txt = fin.read()
    fin.close()
    lines = txt.split('\n')
    lines.pop()
    return lines

def sortedDict(ddict):
    '''turns a dict into a sorted list'''
    sorted_ddict = sorted(ddict.iteritems(), key=operator.itemgetter(1), reverse=True)
    return sorted_ddict

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
def extractName(entry):
    '''If field includes square brackets then this ignores any part of name field which lies outside
       If field contains semicolons then treats thes as separate objects'''
    if u'[' in entry:
        pos1 = entry.find(u'[')
        pos2 = entry.find(u']')
        entry = entry[pos1+1:pos2]
    return entry.split(u';')

def extractNameParts(name):
    '''Tries to separate a name into first and second name.'''
    #Algorithm. If one "," in names then asume lName, fName.
    #Else asume last name is the last word of the name.
    #Plain name returned if all else fails
    if u',' in name:
        parts = name.split(u',')
        if len(parts)==2:
            return u'%s;%s' %(parts[1].strip(),parts[0].strip())
    if u' ' in name:
        parts = name.split(u' ')
        lName = parts[-1].strip()
        fName = name[:-len(lName)].strip()
        return u'%s;%s' %(fName,lName)
    return name

def getWikidata(articles, dDict=None, verbose=False, language='sv', family='wikipedia', old=True):
    '''
    #largely replaced by WikiApi.getPageInfo() - only the simplified formating is  not included
    returns the wikidata enitity id of an article/list of articles or a comment if none can be found
    @input:  article/list of articles
             dDict: dictionary to which to add the results as {article:wikidata} [None]
             verbose: verbose output from wdFormat [False]
             language/family: language and family for api [sv/wikipedia]
             old: option for backwards compatibility wherby only wikidata_entity/None is returned (for a list of articles) [True]
    @output: single article suplied: (wikidata entity, comment) formated through wdFormat()
             list of articles supplied: dictonary as {article:wikidata}
    TO DO: Once "old" can be removed pDict may be bypassed in favour of dDict
    '''
    if not dDict:
        dDict ={}
    single=False
    if not isinstance(articles,list):
        if isinstance(articles,str):
            articles = [articles,]
            single=True
        else:
            print '"getWikidata()" requires a list of articles or a single article as the first parameter.'
            return None
    pDict ={}
    getPageInfo(articles, pDict, language=language, family=family)
    if single:
        return wdFormat(articles[0], pDict[articles[0]], verbose=verbose)
    elif old:
        for k, v in pDict.iteritems():
            pInfo = wdFormat(k, v, verbose=verbose)
            if pInfo[0]:
                dDict[k] = pInfo[0]
            else:
                dDict[k] = None
        return dDict #in case one was not supplied
    else:
        for k, v in pDict.iteritems():
            dDict[k] = v
        return dDict #in case one was not supplied

def getManyWikidata(articles, dDict, verbose=False, language='sv', family='wikipedia'):
    '''
    DEPRECATED, use new getWikidata() instead. Make sure old call is not followed by a call to getPageInfo()
    '''
    print 'getManyWikidata() is DEPRECATED use new getWikidata() instead'
    return getWikidata(article, dDict=dDict, verbose=verbose, language=language, family=family)

def getManyArticles(wikidata, dDict, verbose=False):
    '''
    DEPRECATED to WikiDataApi.getArticles()
    returns the articles of a list of wikidata enitity ids
    '''
    print 'getManyArticles() is DEPRECATED use new WikiDataApi.getArticles() instead'
    if not isinstance(wikidata,list):
        print '"getManyArticles" requiresa list of articles. for individual wikidata entities use "getArticles" instead'
        return None
    #do an upper limit check (max 50 titles per request allowed)
    if len(wikidata) > 50:
        i=0
        while True:
            getManyArticles(wikidata[i:i+50], dDict, verbose=verbose)
            i=i+50
            if i+50 > len(wikidata):
                getManyArticles(wikidata[i:], dDict, verbose=verbose)
                break
    elif len(wikidata) > 0:
        wikiurl = u'https://www.wikidata.org'
        apiurl = '%s/w/api.php' %wikiurl
        urlbase = '%s?action=wbgetentities&format=json&props=sitelinks&ids=' %apiurl
        url = urlbase+urllib.quote('|'.join(wikidata).encode('utf-8'))
        if verbose: print url
        req = urllib2.urlopen(url)
        j = loads(req.read())
        req.close()
        if (j['success'] == 1) or (not 'warnings' in j.keys()) or (not len(j['entities'])==1):
            for k, v in j['entities'].iteritems():
                if 'svwiki' in v['sitelinks'].keys():
                    title = v['sitelinks']['svwiki']['title']
                    dDict[k] = title
                    if verbose: print u'%s: Found the title at %s' %(k,title)
                else:
                    dDict[k] = None
                    if verbose: print '%s: no entry' %k
        else:
            error = 'success: %s, warnings: %s, entries: %d' %(j['success'], 'warnings' in j.keys(), len(j['entities']))
            if verbose: print error
            return (None, error)

def findUnit(contents, start, end, brackets=None):
    '''
    Method for isolating an object in a string. Will not work with either start or end using the ¤ symbol
    @input: 
        * content: the string to look at
        * start: the substring indicateing the start of the object
        * end: the substring indicating the end of the object
            if end is not found then the rest of the string is returned
            if explicitly set to None then it is assumed that start-string also marks the end of an object. In this case the end-string is returned as part of the remainder
        * brackets: a dict of brackets used which must match within the object
    @output:
        the-object, the-remainder-of-the-string, lead-in-to-object
        OR None,None if an error
        OR '','' if no object is found
    '''
    if start in contents:
        #If end is left blank
        if end==None:
            noEnd=True
            end = start
        else:
            noEnd=False
        
        uStart = contents.find(start) + len(start)
        uEnd = contents.find(end,uStart)
        if uEnd < 0: #process till end of string
            uEnd = None
        if brackets:
            for bStart,bEnd in brackets.iteritems():
                dummy=u'¤'*len(bEnd)
                diff = contents[uStart:uEnd].count(bStart) - contents[uStart:uEnd].count(bEnd)
                if diff<0:
                    print 'Negative bracket missmatch for: %s <--> %s' %(bStart,bEnd)
                    return None, None, None
                #two cases either end is one of these brackets or not
                if end in bEnd: #end is part of endBracket
                    i=0
                    while(diff >0):
                        i=i+1
                        uEnd = contents.replace(bEnd,dummy,i).find(end,uStart)
                        if uEnd < 0:
                            print 'Positive (final) bracket missmatch for: %s <--> %s' %(bStart,bEnd)
                            return None, None, None
                        diff = contents[uStart:uEnd].count(bStart) - contents[uStart:uEnd].count(bEnd)
                else: #end is different from endBracket (e.g. a '|')
                    i=0
                    while(diff >0):
                        i=i+1
                        uEnd = contents.find(end,uEnd+len(end))
                        if uEnd < 0:
                            diff = contents[uStart:].count(bStart) - contents[uStart:].count(bEnd)
                            if diff>0:
                                print 'Positive (final) bracket missmatch for: %s <--> %s' %(bStart,bEnd)
                                return None, None, None
                        else:
                            diff = contents[uStart:uEnd].count(bStart) - contents[uStart:uEnd].count(bEnd)
                        
        unit = contents[uStart:uEnd]
        lead_in = contents[:uStart-len(start)]
        if uEnd: #i.e. if not until end of string
            if noEnd:
                remainder = contents[uEnd:]
            else:
                remainder = contents[uEnd+len(end):]
        else:
            remainder = ''
        return (unit, remainder, lead_in)
    else:
        return '','',''

def extractLink(text, kill_tags=False):
    '''
    Given wikitiext this checks for the first wikilink
    Limitations: Only identifies the first wikilink
    kill_tags also strips out (but doesn't keep) and tags (i.e. <bla> something </bla>)
    @output: (plain_text, link)
    '''
    if kill_tags:
        while '<' in text and '>' in text:
            tag, dummy, dummy = findUnit(text, u'<', u'>')
            endtag = u'</'+tag+u'>'
            tag = u'<'+tag+u'>'
            if endtag in text:
                dummy, remainder, lead_in = findUnit(text, tag, endtag)
            else:
                dummy, remainder, lead_in = findUnit(text, u'<', u'>')
            text = lead_in.strip()+' '+remainder.strip()
    
    if not u'[[' in text: return (text.strip(), '')
    interior, dummy, dummy = findUnit(text, u'[[', u']]')
    wikilink = u'[['+interior+u']]'
    pos = text.find(wikilink)
    pre = text[:pos]
    post = text[pos+len(wikilink):]
    center=''
    link=''
    
    #determine which type of link we are dealing with see meta:Help:Links#Wikilinks for details
    if not u'|' in interior: #[[ab]] -> ('ab', 'ab')
        center = interior
        link = interior.strip()
    else:
        pos = interior.find(u'|')
        link = interior[:pos]
        center = interior[pos+1:]
        if len(link) == 0: #[[|ab]] -> ('ab', 'ab')
            link = center
        elif len(center)>0:  #[[a|b]] -> ('b', 'a')
            pass
        else:
            center=link
            if u':' in center:  # [[a:b|]] -> ('b', 'a:b')
                center = center[center.find(u':')+1:]
            if u', ' in center: # [[a, b|]] -> ('a', 'a, b')
                center = center.split(u', ')[0]
            if u'(' in center: #[[a (b)|]] -> ('a', 'a (b)')
                pos = center.find(u'(')
                if u')' in center[pos:]:
                    center=center[:pos]
                    if center.endswith(' '): # the first space separating text and bracket is ignored
                        center = center[:-1]
    return ((pre+center+post).strip(), link.strip())

def extractAllLinks(text, kill_tags=False):
    '''
    Given wikitiext this checks for any wikilinks
    @output: (plain_text, list of link)
    '''
    wikilinks=[]
    text, link = extractLink(text, kill_tags=kill_tags)
    while link:
        wikilinks.append(link)
        text, link = extractLink(text, kill_tags=kill_tags)
    return text, wikilinks

def latLonFromCoord(coord):
    '''
    returns lat, lon as decimals based on string using the Coord-template
    @output (lat,lon) as float
    '''
    if not (coord.startswith(u'{{Coord|') or coord.startswith(u'{{coord|')): print 'incorrectly formated coordinate: %s' %coord; return None
    p = coord.split('|')
    if len(p) >= 9:
        lat_d, lat_m, lat_s, lat_sign = float(p[1].strip()), float(p[2].strip()), float(p[3].strip()), p[4]
        lon_d, lon_m, lon_s, lon_sign = float(p[5].strip()), float(p[6].strip()), float(p[7].strip()), p[8]
        lat = lat_d + lat_m/60 + lat_s/3600
        lon = lon_d + lon_m/60 + lon_s/3600
    elif len(p) >= 5:
        lat, lat_sign = float(p[1].strip()), p[2]
        lon, lon_sign = float(p[3].strip()), p[4]
    if lat_sign == u'N': lat_sign=1
    elif lat_sign == u'S': lat_sign=-1
    else: print 'incorrectly formated coordinate: %s' %coord; return None
    if lon_sign == u'E': lon_sign=1
    elif lon_sign == u'W': lon_sign=-1
    else: print 'incorrectly formated coordinate: %s' %coord; return None
    lat = lat_sign*lat
    lon = lon_sign*lon
    return (lat,lon)

def getPage(page, verbose=False, language='sv', family='wikipedia'):
    '''
    DEPRECATED to WikiApi.getPage()
    Given an article this returns the contents of (the latest revision of) the page
    @ input: pagetitle to look at
    @ output: contents of page
    '''
    print 'getPage() is DEPRECATED use new WikiDataApi.getPage() instead'
    apiurl = u'https://%s.%s.org/w/api.php' %(language, family)
    urlbase = '%s?action=query&prop=revisions&format=json&rvprop=content&rvlimit=1&titles=' %apiurl
    url = urlbase+urllib.quote(page.encode('utf-8'))
    if verbose: print url
    req = urllib2.urlopen(url)
    j = loads(req.read())
    req.close()
    pageid = j['query']['pages'].keys()[0]
    if pageid == u'-1':
        if verbose: print 'no entry for "%s"' %page
        return None
    else:
        content = j['query']['pages'][pageid]['revisions'][0]['*']
        return content

def getPageTimestamp(page, verbose=False, language='sv', family='wikipedia'):
    '''
    DEPRECATED to WikiApi.getTimestamp()
    Given an article this returns the timestamp of (the latest revision of) the page
    @ input: pagetitle to look at
    @ output: timestamp in ISO 8601 format
    '''
    print 'getPageTimestamp() is DEPRECATED use new WikiDataApi.getTimestamp() instead'
    apiurl = u'https://%s.%s.org/w/api.php' %(language, family)
    urlbase = '%s?action=query&prop=revisions&format=json&rvprop=timestamp&rvlimit=1&titles=' %apiurl
    url = urlbase+urllib.quote(page.encode('utf-8'))
    if verbose: print url
    req = urllib2.urlopen(url)
    j = loads(req.read())
    req.close()
    pageid = j['query']['pages'].keys()[0]
    if pageid == u'-1':
        if verbose: print 'no entry for "%s"' %page
        return None
    else:
        content = j['query']['pages'][pageid]['revisions'][0]['timestamp']
        return content

def getPageInfo(articles, dDict, verbose=False, language='sv', family='wikipedia'):
    '''
    DEPRECATED to WikiApi.getPageInfo()
    Given a list of articles this tells us if the page is either of
    * Non-existent (red link)
    * A redirect (and returns real page)
    * A disambiguity page
    * Normal page
    and whether the page corresponds to a wikidata entry (and returns the wikidata id)
    @input: a list of pagenames or a single pagename
    @output: fills in the supplied dict with the supplied pagenames and a dict of properties with possible parameters being: redirected, missing, disambiguation, wikidata
    '''
    print 'getPageInfo() is DEPRECATED use new WikiDataApi.getPageInfo() instead'
    if not isinstance(articles,list):
        if isinstance(articles,str):
            articles = [articles,]
        else:
            print '"getPageInfo" requires a list of pagenames or a single pagename.'
            return None
    #do an upper limit check (max 50 titles per request allowed)
    if len(articles) > 50:
        i=0
        while True:
            getPageInfo(articles[i:i+50], dDict, verbose=verbose, language=language, family=family)
            i=i+50
            if i+50 > len(articles):
                getPageInfo(articles[i:], dDict, verbose=verbose, language=language, family=family)
                break
    elif len(articles) > 0:
        apiurl = u'https://%s.%s.org/w/api.php' %(language, family)
        urlbase = u'%s?action=query&prop=pageprops&format=json&redirects=&titles=' %apiurl
        url = urlbase+urllib.quote('|'.join(articles).encode('utf-8'))
        if verbose: print url
        req = urllib2.urlopen(url)
        j = loads(req.read())
        req.close()
        
        #start with redirects
        rDict = {}
        if 'redirects' in j['query'].keys():
            redirects = j['query']['redirects'] #a list
            for r in redirects:
                rDict[r['to']] = r['from']
        
        #then pages
        pages = j['query']['pages'] #a dict
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

def getAdvancedWikidata(article, verbose=False, language='sv', family='wikipedia'):
    '''
    Given a single article this checks for a corresponding wikidata entry
    and formats the output
    DEPRECATED, use new getWikidata() instead
    '''
    print 'getAdvancedWikidata() is DEPRECATED use new getWikidata() instead'
    return getWikidata(article, verbose=verbose, language=language, family=family)

def wdFormat(article, pInfo, verbose=False):
    '''
    Formats a single entry from the output of getPageInfo()
    * If the page is not a disambiguation page and a wikidata entry is found then this 
      is returned as the first parameter
    * Else if the page is a DISAMBIGUATION, RED LINK or LACKS A WIKIDATA ENTITY this is returned as a second 
      parameter (disambig, redLink, normal)
    @ output (wikidata entity, comment)
    '''
    if 'disambiguation' in pInfo.keys():
        if verbose: print u'%s: was a disambiguation page' % article
        return (None, 'disambig')
    elif 'wikidata' in pInfo.keys():
        if verbose: print u'%s: has wikidata entry at %s' %(article,pInfo['wikidata'])
        return (pInfo['wikidata'], None)
    elif 'missing' in pInfo.keys():
        if verbose: print u'%s: was a red link' % article
        return (None, 'redLink')
    else:
        if verbose: print u'%s: needs a wikidata entry' % article
        #add mechanism for creating wikidata entry
        return (None, 'normal')
#done
