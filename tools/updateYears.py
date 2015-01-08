#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tool for scraping artistYears from sv.wiki articles and updating these in the ÖDOK database
once possible use Property:P569 and Property:P570 on wikidata instead/as well
'''
import dconfig as config
import odok as odokConnect
import WikiApi as wikiApi
import common as common
import codecs

def getArtists(dbWriteSQL):
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
    affected_count, results = dbWriteSQL.query(query, None, expectReply=True)
    print u'got %d artists with missing years' % affected_count
    artists = []
    for row in results:
        (idNo, wikidata, birth_year, death_year) = row
        artists.append({u'id':idNo, u'wikidata':wikidata, u'birth_year':birth_year, u'death_year':death_year, u'svwiki':None})
    return artists

def getArticles(wdApi, artists, verbose=False):
    '''
    Queries Wikidata's API to find the articles corresponding to each wikidata entry
    @ input: list of aritst each as a dict {id, wikidata, birth_year, death_year, svwiki}
    '''
    # make list of wikidata only
    wikidata=[]
    for a in artists:
        wikidata.append(a[u'wikidata'])
    
    # get articles
    dataToArticle = wdApi.getArticles(wikidata, debug=verbose, site=u'svwiki')
    #match
    for a in artists:
        a[u'svwiki'] = dataToArticle[a[u'wikidata']]

def getYears(wpApi, artists, verbose=False):
    '''
    Identifies any artists with updated years by looking at the relevant categoires at the sv.Wikipedia page for said artist
    @ input: list of aritst each as a dict {id, wikidata, birth_year, death_year, svwiki}
    @ output list of changed artists each as a dict {id, wikidata, birth_year, death_year, svwiki}
    '''
    withSvWiki = {}
    for a in artists:
        if a[u'svwiki'] and a[u'svwiki']['title']:
            withSvWiki[a[u'id']] = a[u'svwiki']['title']
    catDict = wpApi.getPageCategories(withSvWiki.values(), nohidden=True, dDict=None, debug=verbose)
    
    changedArtists=[]
    for a in artists:
        changed = False
        idNo = a[u'id']
        if idNo in withSvWiki.keys():
            if not withSvWiki[idNo] in catDict.keys():
                print 'no entry for "%s". This should never happen!' %withSvWiki[idNo]
                continue
            (birth, death) = getYearCats(catDict[withSvWiki[idNo]],withSvWiki[idNo])
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

def getYearCats(catList, article):
    '''
    Analyses the sv.Wikipedia categories in an article to isolate information related to birth/death
    @ input: list of categories
    @ output: (birth_year, death_year)
    '''
    birth=None
    death=None
    
    if not catList:
        print 'no category for "%s" or page did not exist' %article
    else:
        for c in catList:
            if c.lower().startswith(u'kategori:avlidna'):
                if common.is_number(c.strip()[-4:]): death = int(c.strip()[-4:])
                else: print u'odd year for %s: %s' %(article, c)
            elif c.lower().startswith(u'kategori:födda'):
                if common.is_number(c.strip()[-4:]): birth = int(c.strip()[-4:])
                else: print u'odd year for %s: %s' %(article, c)
    return (birth, death)

def uppdateArtist(dbWriteSQL, artists, testing):
    '''
    SQL UPDATE artist_table
        to do: times out even for only a few updates...
    '''
    print u'got %d artists to update' % len(artists)
    for a in artists:
        vals = []
        query = u"""UPDATE `artist_table` SET """
        if a[u'birth_year']:
            query = query+u"""`birth_year`=%r"""
            vals.append(a[u'birth_year'])
        if a[u'death_year']:
            if a[u'birth_year']: query = query+u""", `death_year`=%r"""
            else: query = query+u"""`death_year`=%r"""
            vals.append(a[u'death_year'])
        query = query+u""" WHERE `id` = %s;\n"""
        vals.append(a[u'id'])
        dbWriteSQL.query(query[:-1], tuple(vals), expectReply=False, testing=testing)

def run(testing=False):
    '''
    runs the whole process. if testing=True then outputs to file instead
    '''
    dbWriteSQL = odokConnect.OdokWriter.setUp(host=config.db_server, db=config.db, user=config.db_edit, passwd=config.db_edit_password)
    wpApi = wikiApi.WikiApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wp_site)
    wdApi = wikiApi.WikiDataApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wd_site)
    
    artists = getArtists(dbWriteSQL)
    getArticles(wdApi, artists, verbose=False)
    changedArtists = getYears(wpApi, artists)
    for c in changedArtists:
        print '%d\t%r\t%r\t%s' %(c[u'id'], c[u'birth_year'], c[u'death_year'], c[u'svwiki']['title'])
    if len(changedArtists)>0:
        uppdateArtist(dbWriteSQL, changedArtists, testing)
    output = dbWriteSQL.closeConnections()
    if testing:
        f=codecs.open('scrapeYears.sql','w','utf8')
        f.write(output)
        f.close()
        print u'File with sqlcode to be run can be found at scrapeYears.sql'
    print u'Done!'
    exit(1)

if __name__ == "__main__":
    run()
