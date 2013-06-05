#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Temporary tool for scraping artistYears from sv.wiki articles and udating these in the ÖDOK database
    once possible use Property:P569 and Property:P570 on wikidata instead
'''
import dconfig as dconfig
from common import Common
import MySQLdb
import codecs
import urllib, urllib2
from json import loads
import time

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(host=dconfig.db_server, db=dconfig.db, user = dconfig.db_username, passwd = dconfig.db_password, use_unicode=True, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def getArtists(conn, cursor):
    '''
    Queries the ÖDOK database and returns all artists with a wikidata entry
    missing at least one year.
    @ output: list of aritst each as a dict {id, wikidata, birth_year, death_year, svwiki}
    '''
    query=u"""SELECT `id`, `wiki`, `birth_year`, `death_year` FROM `artist_table` WHERE 
    `wiki` != '' 
    AND (
        `death_year` IS NULL
        OR
        `birth_year` IS NULL
    );"""
    affected_count = cursor.execute(query)
    print u'got %d artists to update' % affected_count
    artists = []
    for row in cursor:
        (idNo, wikidata, birth_year, death_year) = row
        artists.append({u'id':idNo, u'wikidata':wikidata.lower(), u'birth_year':birth_year, u'death_year':death_year, u'svwiki':None})
    return artists

def getArticles(artists, verbose=False):
    '''
    Queries Wikidata's API to find the articles corresponding to each wikidata entry
    @ input: list of aritst each as a dict {id, wikidata, birth_year, death_year, svwiki}
    '''
    # make list of wikidata only
    wikidata=[]
    for a in artists:
        wikidata.append(a[u'wikidata'])
    # get articles
    dataToArticle={}
    Common.getManyArticles(wikidata, dataToArticle, verbose=verbose)
    #match
    for a in artists:
        a[u'svwiki'] = dataToArticle[a[u'wikidata']]

def getYears(artists, verbose=False):
    '''
    Identifies any artists with updated years
    @ input: list of aritst each as a dict {id, wikidata, birth_year, death_year, svwiki}
    @ output list of changed artists each as a dict {id, wikidata, birth_year, death_year, svwiki}
    '''
    #due to a oddly designed limit on categories each page must be queried separately
    changedArtists=[]
    for a in artists:
        changed = False
        if a[u'svwiki']:
            #time.sleep(1) #wait for 1 second
            (birth, death) = getYearCats(a[u'svwiki'], verbose=verbose)
            if not a[u'birth_year'] and birth:
                changed = True
                a[u'birth_year'] = birth
            if not a[u'death_year'] and death:
                changed = True
                a[u'death_year'] = death
        if changed:
            changedArtists.append(a)
    print u'Identified %r changed artists' % len(changedArtists)
    return changedArtists

def getYearCats(article, verbose=False):
    '''
    Queries the sv.Wikipedia API to find categories in an article related to birth/death
    @ output: (birth_year, death_year)
    '''
    birth=None
    death=None
    wikiurl = u'https://sv.wikipedia.org'
    apiurl = '%s/w/api.php' %wikiurl
    urlbase = '%s?action=query&prop=categories&format=json&clshow=!hidden&titles=' %apiurl
    url = urlbase+urllib.quote(article.encode('utf-8'))
    if verbose: print url
    req = urllib2.urlopen(url)
    j = loads(req.read())
    req.close()
    pages = j['query']['pages']
    if pages.keys()[0] == u'-1':
        print 'no entry for "%s"' %article
        return (birth, death)
    elif not 'categories' in pages[pages.keys()[0]].keys():
        print 'no category for "%s"' %article
        return (birth, death)
    else:
        cats = pages[pages.keys()[0]]['categories']
        for c in cats:
            if c['title'].lower().startswith(u'kategori:avlidna'):
                if Common.is_number(c['title'].strip()[-4:]): death = int(c['title'].strip()[-4:])
                else: print u'odd year for %s: %s' %(article, c['title'])
            if c['title'].lower().startswith(u'kategori:födda'):
                if Common.is_number(c['title'].strip()[-4:]): birth = int(c['title'].strip()[-4:])
                else: print u'odd year for %s: %s' %(article, c['title'])
        return (birth, death)

def uppdateArtist(conn, cursor, artists, testing):
    '''
    SQL UPDATE artist_table
        to do: times out even for only a few updates...
    '''
    query = u""""""
    vals = []
    for a in artists:
        query = query+u"""UPDATE `artist_table` SET """
        if a[u'birth_year']:
            query = query+u"""`birth_year`=%r"""
            vals.append(a[u'birth_year'])
        if a[u'death_year']:
            if a[u'birth_year']: query = query+u""", `death_year`=%r"""
            else: query = query+u"""`death_year`=%r"""
            vals.append(a[u'death_year'])
        query = query+u""" WHERE `id` = %s;\n"""
        vals.append(a[u'id'])
    if testing:
        f=codecs.open('scrapeYears.sql','w','utf8')
        f.write(query[:-1] %conn.literal(tuple(vals)))
        f.close()
    else:
        affected_count = cursor.execute(query[:-1], tuple(vals))
        print u'got %d artists to update' % affected_count

def run(testing=True):
    '''
    runs the whole process. if testing=true then outputs to file instead
    '''
    (conn, cursor) = connectDatabase()
    artists = getArtists(conn, cursor)
    getArticles(artists, verbose=False)
    changedArtists = getYears(artists)
    for c in changedArtists:
        print '%d\t%r\t%r\t%s' %(c[u'id'], c[u'birth_year'], c[u'death_year'], c[u'svwiki'])
    if len(changedArtists)>0:
        uppdateArtist(conn, cursor, changedArtists, testing)
    conn.close()
    print u'Done!'
