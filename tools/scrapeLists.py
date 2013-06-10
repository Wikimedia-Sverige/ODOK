#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Temporary tool for scraping artistYears from sv.wiki articles and udating these in the ÖDOK database
    once possible use Property:P569 and Property:P570 on wikidata instead
'''
import dconfig as dconfig
import common as common
import MySQLdb
import codecs
import urllib, urllib2
from json import loads
import time

def getPage(page, verbose=False):
    '''
    Queries the sv.Wikipedia API to return the contents of a given page
    @ input: page to look at
    @ output: contents of page
    '''
    wikiurl = u'https://sv.wikipedia.org'
    apiurl = '%s/w/api.php' %wikiurl
    urlbase = '%s?action=query&prop=revisions&format=json&rvprop=content&rvlimit=1&titles=' %apiurl
    url = urlbase+urllib.quote(page.encode('utf-8'))
    if verbose: print url
    req = urllib2.urlopen(url)
    j = loads(req.read())
    req.close()
    pageid = j['query']['pages'].keys()[0]
    if pageid == u'-1':
        print 'no entry for "%s"' %page
        return None
    else:
        content = j['query']['pages'][pageid]['revisions'][0]['*']
        return content

def parseArtwork(contents):
    '''
    Given the contents of a wikipage this returns the artorks listed in it
    input: wikicode
    @ output: list of artwork-dict items
    '''
    units=[]
    while(True):
        table, contents, lead_in = common.findUnit(contents, u'{{Skulpturlista-huvud}}', u'|}')
        if not table: break
        #try to isolate a header row
        header=''
        lead_rows = lead_in.strip(' \n').split('\n')
        if lead_rows[-1].startswith(u'=='):
            header = lead_rows[-1].strip(u' =')
        while(True):
            unit, table, dummy = common.findUnit(table, u'{{Skulpturlista', u'}}', brackets={u'{{':u'}}'})
            if not unit: break
            params={}
            u = {u'id':'', u'namn':'', u'skulptör':'', u'årtal':'', u'material':'', u'plats':'', u'koordinater':'', u'bild':'', u'header':'', u'namn_link':'', u'skulptör_link':'', u'plats_link':''}
            u[u'header']=header
            while(True):
                part, unit, dummy = common.findUnit(unit, u'|', u'\n', brackets={u'[[':u']]', u'{{':u'}}'})
                if not part: break
                if u'=' in part:
                    part = part.replace(u'<small>','').replace(u'</small>','')
                    part=part.strip(' \n\t')
                    #can't use split as coord uses second equality sign
                    pos = part.find(u'=')
                    key=part[:pos].strip()
                    value=part[pos+1:].strip()
                    if len(value) > 0:
                        if (key) in u.keys(): u[key] = value
                        else: print u'Unrecognised parameter: %s = %s' %(key, value)
            units.append(u.copy())
            #end units
        #end tables
    return units

def postProcessing(units):
    '''
    proceses output of parseArtwork() and matches it to parameter names in ödok
    delinking plats, keeping track of artist link, fixing coords
    '''
    for u in units:
        if u[u'koordinater']:
            u[u'koordinater'] = common.latLonFromCoord(u[u'koordinater'])
        if u[u'skulptör']:
            u[u'skulptör'], u[u'skulptör_link'] = common.extractLink(u[u'skulptör'])
        if u[u'plats']:
            u[u'plats'], u[u'plats_link'] = common.extractLink(u[u'plats'])
        if u[u'namn']:
            u[u'namn'], u[u'namn_link'] = common.extractLink(u[u'namn'])

def getOdokHits(queries, dDict, verbose=False):
    '''
    Given constrictions (as a dict) this returns the available ODOK results using the get method of the api
    @ output: None if successful. Otherwise errormessage
    '''
    params={}
    for k,v in queries.iteritems():
        params[k] = v.encode('utf-8')
    apiurl = 'http://wlpa.wikimedia.se/odok-bot/api.php'
    urlbase = '%s?action=get&limit=100&format=json&' %apiurl
    url = urlbase+urllib.urlencode(params)
    if verbose: print url
    req = urllib2.urlopen(url)
    j = loads(req.read())
    req.close()
    if (j['head']['status'] == 1) or (not 'warning' in j['head'].keys()):
        for hit in j['body']:
            idNo = hit['hit']['id']
            dDict[idNo]=hit['hit']
        #get all results
        if 'continue' in j['head'].keys():
            offset = j['head']['continue']
            queries['offset']=str(offset)
            getOdokHits(queries, dDict, verbose=verbose)
        else:
            return None
    else:
        warning=''
        if j['head']['warning']: warning=j['head']['warning']
        error = 'status: %s, warning: %s' %(j['head']['status'], warning)
        if verbose: print error
        return error

def findMatches(odok, wiki):
    '''
    tries to find matches between scraped items and exisiting odok items
    identified matches has the odok id added to the wiki object
    TO DO: Expand to display several alternatives
    '''
    #remove any id's which have already been identified
    matched_ids=[]
    for w in wiki:
        if w['id']:
            if w['id'] in matched_ids:
                print u'id %s was matched to more than one wiki object!' %w['id']
            else:
                matched_ids.append(w['id'])
    print u'%r out of %r already matched (out of a maximum of %r)' %(len(matched_ids), len(wiki), len(odok))
    #make lists of odok titles and artists
    odok_titles={}; odok_artist={}
    for key, o in odok.iteritems():
        if key in matched_ids: continue
        if o['title']: 
            if o['title'] in odok_titles.keys(): odok_titles[o['title']].append(key)
            else: odok_titles[o['title']] = [key,]
        if o['artist']:
            if o['artist'] in odok_artist.keys(): odok_artist[o['artist']].append(key)
            else: odok_artist[o['artist']] = [key,]
    #remove any id's which have already been identified
    for w in wiki:
        if w['id']: continue
        wIdN = None; wIdA=None; match = (None,'')
        if w['namn'] in odok_titles.keys():
            wIdN = odok_titles[w['namn']]
        if w[u'skulptör'] in odok_artist.keys():
            wIdA = odok_artist[w[u'skulptör']]
        if wIdN and wIdA: #match on both title and artist
            if len(wIdN) == 1:
                if wIdN[0] in wIdA: match = (wIdN[0], 'double match')
                else: match = (wIdN[0], 'title match but artist missmatch')
            else:
                for nId in wIdN:
                    if nId in wIdA:
                        match = (nId, 'Non unique title with artist match')
                        break
        elif wIdN: #match on title only
            if len(wIdN) == 1:
                match = (wIdN[0], 'titel match') 
        elif wIdA: #match on artist only
            if len(wIdA) == 1:
                match = (wIdA[0], 'artist match') 
        #explicitly ask for verification for each match
        if match[0]:
            key=match[0]
            print u'%s: (%s)' %(match[1], key)
            print u'W: "%s", "%s", "%s"' %(w[u'namn'], w[u'skulptör'], w[u'årtal'])
            print u'Ö: "%s", "%s", "%s"' %(odok[key]['title'], odok[key][u'artist'], odok[key][u'year'])
            while True:
                inChoice=raw_input('Accept? [Y/N]:')
                if inChoice == 'Y' or inChoice == 'y':
                    w['id'] = key
                    break
                elif inChoice == 'N' or inChoice == 'n':
                    break

def fileToHits(filename):
    '''
    opens an outputfile from run() and returns it as a list of dicts
    '''
    lines = common.openFile(filename)
    wikiHits = []
    for l in lines:
        parts = l.split('|')
        unit = {}
        for p in parts:
            if p:
                key = p.split(':')[0]
                value = p[len(key)+1:]
                unit[key]=value
        wikiHits.append(unit.copy())
    return wikiHits

def run(testing=True, pages=[], queries ={}, listFile=None):
    '''
    runs the whole process. if testing=true then outputs to file instead
    '''
    if testing:
        pages.append(u'Användardiskussion:André_Costa_(WMSE)/tmp')
        queries['muni'] = '0180'
    if listFile:
        wikiHits=fileToHits(listFile)
    else:
        wikiHits=[]
        for page in pages:
            contents = getPage(page=page, verbose=False)
            wikiHits = wikiHits + parseArtwork(contents)
            print u'wikiHits: %r' %len(wikiHits)
        postProcessing(wikiHits)
        #safety backup
        f=codecs.open('scrapetmp1.txt','w','utf8')
        for u in wikiHits:
            for k,v in u.iteritems():
                if k == u'koordinater':
                    if v: f.write(u'lat:%r|lon:%r|' %u[u'koordinater'])
                    else: f.write(u'lat:|lon:|')
                else: f.write(u'%s:%s|' %(k,v))
            f.write(u'\n')
        f.close()
    #fetch all objects matching a given constriction
    odokHits={}
    odok_result = getOdokHits(queries, odokHits)
    if odok_result:
        print odok_result
        exit(0)
    #match primarily based on title, or title+artist (but ask for each)
    findMatches(odokHits, wikiHits)
    #compare values (focus on stadsdel, plats, koord, material, bild, artist_link) be distrustful of name_link and beware of <ref>
    #add new values to ÖDOK
    f=codecs.open('scrapetmp.txt','w','utf8')
    for u in wikiHits:
        for k,v in u.iteritems():
            if k == u'koordinater':
                if v: f.write(u'lat:%r|lon:%r|' %u[u'koordinater'])
                else: f.write(u'lat:|lon:|')
            else: f.write(u'%s:%s|' %(k,v))
        f.write(u'\n')
    f.close()
    print 'Done!'
