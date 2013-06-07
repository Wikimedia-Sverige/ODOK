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
        print 'no entry for "%s"' %article
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
            u = {u'namn':'', u'skulptör':'', u'årtal':'', u'material':'', u'plats':'', u'koordinater':'', u'bild':'', u'header':'', u'namn_link':'', u'skulptör_link':'', u'plats_link':''}
            u[u'header']=header
            while(True):
                part, unit, dummy = common.findUnit(unit, u'|', u'\n', brackets={u'[[':u']]', u'{{':u'}}'})
                if not part: break
                if u'=' in part:
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

def run(testing=True):
    '''
    runs the whole process. if testing=true then outputs to file instead
    '''
    contents = getPage(page=u'Användardiskussion:André_Costa_(WMSE)/tmp', verbose=True)
    units = parseArtwork(contents)
    postProcessing(units)
    #match units objects in ÖDOK
    ##fetch all objects matchin a given limitation (e.g. muni=0180)
    ##match primarily based on title, or title+artist (but ask for each)
    #compare values (focus on stadsdel, plats, koord, material, bild, artist_link) be distrustful of name_link and beware of <ref>
    #add new values to ÖDOK
    if testing:
        f=codecs.open('scrapetmp.txt','w','utf8')
        for u in units:
            f.write(u'------\n')
            if u[u'koordinater']: u[u'koordinater'] = u'lat=%r, lon=%r' % u[u'koordinater']
            for k,v in u.iteritems():
                f.write(u'%s:\t\t%s\n' %(k,v))
        f.close()
    print 'Done!'
