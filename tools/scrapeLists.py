#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
 Tool for scraping existing artwork lists from sv.wiki and attempting to match these to existing posts in the database.
 How to use: 
 
 == Initial scraping ==
 1. Identify pages with relevant lists. store pagenames as list <pages>
 2. Identify municipalitynumber as <muniNo>
 3. Do initial scrape:
        run(testing=False, pages=<pages>, queries={'muni':'<muniNo>'}, tmpFile=u'scrapetmp.txt')
 3.1 Results are outputted into <scrapetmp.txt>
 3.2 For further scrapes use
        run(testing=False, queries={'muni':'<muniNo>'}, listFile=u'scrapetmp1.txt')
 ?Does anythin have to be done manually at this point?
 == Comparison of scraped results to database objects ==
 4. Do the first quick update which adds only enhancing data
        runUpdates(u'scrapetmp.txt', queries={'muni':'<muniNo>'}, quick=True)
        Manually ok article suggestions
        commitUpdatesFil('tmpUpdates.txt', testing=False)
 ?must original artistLinks be dealt with here?
 5. Do the longer manual update (can be done repetedly)
        runUpdates(u'tmpPostponed.txt', queries={'muni':'<muniNo>'})   !Note that this loses and _link parameters in the postponed file
        commitUpdatesFil('tmpUpdates.txt', testing=False)
 6. Linked artists can be dealt with separately
        runArtistLinks(u'tmpArtistLinks.txt', verbose=False)
        Manual edits might be required for disambiguations etc. these appear in <tmpArtistLinks2.txt>
    
 
 Updates:
 Starting from the scraped file
 runUpdates(u'scrapetmp-Sthlm.txt', queries={'muni':'0180'}, quick=True)
'''
import dconfig as dconfig
import common as common
import MySQLdb
import codecs
import urllib, urllib2
from json import loads
import time

def parseArtwork(contents, pagename):
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
            u = {u'id':'', u'namn':'', u'skulptör':'', u'årtal':'', u'material':'', u'plats':'', u'koordinater':'', u'bild':'',
                 u'namn_link':'', u'skulptör_link':'', u'plats_link':'',  u'lat':'',  u'lon':'',
                 u'header':header,  u'page':pagename}
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
            u[u'lat'], u[u'lon'] = common.latLonFromCoord(u[u'koordinater'])
        if u[u'skulptör']:
            u[u'skulptör'], u[u'skulptör_link'] = common.extractAllLinks(u[u'skulptör'])
        if u[u'plats']:
            u[u'plats'], u[u'plats_link'] = common.extractAllLinks(u[u'plats'])
        if u[u'namn']:
            u[u'namn'], u[u'namn_link'] = common.extractAllLinks(u[u'namn'])

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

def wash(surname):
    '''
    simplifies a given surname so as to increase the chances of matching
    different spellings.
    There must be a library somewhere for this
    '''
    surname = surname.lower()
    surname = surname.replace(u'ch',u'k').replace(u'c',u'k')
    surname = surname.replace(u'z',u's').replace(u'ß',u's').replace(u'ss',u's')
    surname = surname.replace(u'é',u'e').replace(u'é',u'è')
    surname = surname.replace(u'á',u'a').replace(u'à',u'a')
    surname = surname.replace(u'ø',u'ö')
    surname = surname.replace(u'aa',u'å')
    surname = surname.replace(u'ü',u'y')
    surname = surname.replace(u'q',u'k')
    surname = surname.replace(u'u',u'v')
    return surname

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
    odok_titles={}; odok_artist={}; odok_surname={}
    for key, o in odok.iteritems():
        if key in matched_ids: continue
        if o['title']: 
            if o['title'] in odok_titles.keys(): odok_titles[o['title']].append(key)
            else: odok_titles[o['title']] = [key,]
        if o['artist']:
            if o['artist'] in odok_artist.keys(): odok_artist[o['artist']].append(key)
            else: odok_artist[o['artist']] = [key,]
            surname = wash(o['artist'].split(' ')[-1])
            if surname in odok_surname.keys(): odok_surname[surname].append(key)
            else: odok_surname[surname] = [key,]
    
    #remove any id's which have already been identified
    for w in wiki:
        if w['id']: continue
        wIdN = None; wIdA=None; wIdS=None; match=([], '')
        if w['namn'] in odok_titles.keys():
            wIdN = odok_titles[w['namn']]
        if w[u'skulptör'] in odok_artist.keys():
            wIdA = odok_artist[w[u'skulptör']]
        if wash(w[u'skulptör'].split(' ')[-1]) in odok_surname.keys():
            wIdS = odok_surname[wash(w[u'skulptör'].split(' ')[-1])]
        if wIdN and wIdA: #match on both title and artist
            if len(wIdN) == 1:
                if wIdN[0] in wIdA: match = ([wIdN[0]], 'double match')
                else: match = ([wIdN[0]], 'title match but artist missmatch')
            else:
                for nId in wIdN:
                    if nId in wIdA:
                        match = ([nId], 'Non unique title with artist match')
                        break
        elif wIdN: #match on title only
            match = (wIdN, 'titel match') 
        elif wIdA: #match on artist only
            match = (wIdA, 'artist match') 
        elif wIdS: #last ditch attempt matching surname.
            match = (wIdS, 'surname match')
            #always check this of no match?
            #replace do "nice search" with ss->s
        #explicitly ask for verification for each match
        if match[0]:
            keys=match[0]
            print u'%s: (%s)' %(match[1], ' | '.join(keys))
            print u'W: "%s", "%s", (%s), "%s"' %(w[u'namn'], w[u'skulptör'], w[u'årtal'], w['plats'])
            for r in range(0,len(keys)):
                key = keys[r]
                print u'%r: "%s", "%s", (%s), "%s"' %(r, odok[key]['title'], odok[key][u'artist'], odok[key][u'year'], odok[key][u'address'])
            while True:
                inChoice=raw_input('Accept? [#/N]:')
                if inChoice == 'N' or inChoice == 'n':
                    break
                elif common.is_number(inChoice) and int(inChoice) in range(0,len(keys)):
                    w['id'] = keys[int(inChoice)]
                    break

def fileToHits(filename):
    '''
    opens an outputfile from run() and returns it as a list of dicts
    Move to common.py
    '''
    lines = common.openFile(filename)
    wikiHits = []
    for l in lines:
        parts = l.split('|')
        unit = {}
        for p in parts:
            if p:
                key = p.split(':')[0]
                value = p[len(key)+1:] #cannot use a basic split since parameter may contain aditional colons
                if key.endswith(u'_link') and value:
                    if ';' in value:
                        value = value.split(';')
                    else:
                        value = [value,]
                unit[key]=value
        wikiHits.append(unit.copy())
    return wikiHits

def run(testing=True, pages=[], queries ={}, listFile=None, tmpFile=u'scrapetmp.txt'):
    '''
    runs the scrape-and-match process. if testing=true then outputs to file instead
    '''
    if testing:
        pages.append(u'Användardiskussion:André_Costa_(WMSE)/tmp')
        queries['muni'] = '0180'
    if listFile:
        wikiHits=fileToHits(listFile)
    else:
        wikiHits=[]
        for page in pages:
            contents = common.getPage(page=page, verbose=False)
            wikiHits = wikiHits + parseArtwork(contents, page)
            print u'wikiHits: %r' %len(wikiHits)
        postProcessing(wikiHits)
        #safety backup
        f=codecs.open(u'%s1%s' %(tmpFile[:-4],tmpFile[-4:]),'w','utf8')
        for u in wikiHits:
            for k,v in u.iteritems():
                if isinstance(v,list): #i.e. the non-empty  _link parameters
                    f.write(u'%s:%s|' %(k,';'.join(v)))
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
    f=codecs.open(tmpFile,'w','utf8')
    for u in wikiHits:
        for k,v in u.iteritems():
                if isinstance(v,list): #i.e. the non-empty  _link parameters
                    f.write(u'%s:%s|' %(k,';'.join(v)))
                else: f.write(u'%s:%s|' %(k,v))
        f.write(u'\n')
    f.close()
    print 'Done!'

def outputMissing(listFile, county, muni, wikilist=u'scrapetmp-Sthlm.txt'):
    '''given the previous list file this outputs any unmatched entries'''
    wiki=fileToHits(wikilist)
    missing = []
    for w in wiki:
        if not w['id']:
            missing.append(w.copy())
    print 'Missing %r out of %r' %(len(missing), len(wiki))
    f=codecs.open('%s-missing.%s' %(listFile[:-4],listFile[-3:]),'w','utf8')
    f.write(u'{{Offentligkonstlista-huvud|kommun=%s}}\n' %muni)
    for m in missing:
        f.write(u'%s\n' %wikiListFormat(m,county, muni))
    f.write(u'|}\n')
    f.close()
    print 'Done!'

def outputAll(listFile, county, muni):
    '''given the previous list file this outputs any unmatched entries'''
    wiki=fileToHits(listFile)
    missing = []
    f=codecs.open('%s-asList.%s' %(listFile[:-4],listFile[-3:]),'w','utf8')
    f.write(u'{{Offentligkonstlista-huvud|kommun=%s}}\n' %muni)
    for w in wiki:
        f.write(u'%s\n' %wikiListFormat(w,county, muni))
    f.write(u'|}\n')
    f.close()
    print 'Done!'

def wikiListFormat(w, county, muni):
    '''given a list entry this outputs a wikilist row'''
    if w[u'id']: idNo=w[u'id']
    else: idNo = ''
    
    if w[u'namn']:
        title = w[u'namn']
        if w[u'namn_link']: 
            title = u'%s: [[%s]]' %(title, ']]; [['.join(w[u'namn_link']))
    else: title = ''
    
    if w[u'skulptör']:
        artist = w[u'skulptör']
        if w[u'skulptör_link']: 
            if len(w[u'skulptör_link'])==1:
                if w[u'skulptör_link'][0] == w[u'skulptör']: artist = u'[[%s]]' %artist
                else: artist = u'[[%s|%s]]' %(w[u'skulptör_link'][0], artist)
            else: artist = u'%s: [[%s]]' %(artist, ']]; [['.join(w[u'skulptör_link']))
    else: artist = ''
    
    if w[u'årtal']: year=w[u'årtal']
    else: year = ''
    
    if w[u'material']: material=w[u'material']
    else: material = ''
    
    if w[u'plats']:
        plats = w[u'plats']
        if w[u'plats_link']: 
            plats = u'%s: [[%s]]' %(plats, ']]; [['.join(w[u'plats_link']))
    else: plats = ''
    
    if w[u'header']: stadsdel=w[u'header']
    else: stadsdel = ''
    
    if w[u'lat']: lat=w[u'lat']
    else: lat = ''
    
    if w[u'lon']: lon=w[u'lon']
    else: lon = ''
    
    if w[u'bild']: bild=w[u'bild']
    else: bild = ''
    
    txt = u'''{{Offentligkonstlista|döljKommun=
| id           = %s
| id-länk      = 
| titel        = %s
| artikel      = 
| konstnär     = %s
| årtal        = %s
| beskrivning  = källa: [[%s]]
| typ          = 
| material     = %s
| fri          = 
| plats        = %s
| inomhus      = 
| stadsdel     = %s
| lat          = %s
| lon          = %s
| bild         = %s
| commonscat   = 
}}''' %(idNo, title, artist, year, w['page'], material, plats, stadsdel, lat, lon, bild)
    return txt

#==============================================================================
#Comparison of matched results to database and import of additional data

def updatesToDatabase(odok, wiki, quick=False):
    '''
    given a wiki-entry which has been matched to an odok object
    this checks whether any of the wikiinfo should be added to the odok
    object and prepares an update statement.
    setting quick to true puts any updates requiring decision making into the postponed output
    '''
    updated = {}
    postponed = {}
    linked_artists = {}
    mapping = {u'namn':'title', u'skulptör':'artist', u'årtal':'year', 
               u'material':'material', u'plats':'address', u'header':'district', 
               u'lat':'lat', u'lon':'lon', u'bild':'image', u'typ':'type'}
    #non-trivial mappings u'namn_link':'wiki_article'
    for w in wiki:
        if not w['id']: continue
        o = odok[w['id']]
        changes = {}
        skipped = {}
        for k, v in mapping.iteritems():
            if not k in w.keys(): #for postponed file some fields might be missing
                continue
            no_Tags, dummy = common.extractLink(w[k], kill_tags=True)
            if not no_Tags: #skip if w[k] is empty (or only a tag)
                continue
            if (not o[v]) and no_Tags: #trivial case of new info
                changes[v] = no_Tags
            elif o[v] and (not o[v].lower() == no_Tags.lower()):
                if quick:
                    skipped[k] = w[k]
                else:
                    #need to decide which to use
                    print u'Diff for %s (%s): %s' %(w['id'], o['title'], v)
                    print u' ödok: "%s"' %o[v]
                    print u' wiki: "%s"' %w[k]
                    while True:
                        inChoice=raw_input(u'Use wiki [Y(es)/N(o)/S(kip)]:')
                        if inChoice.lower() == u'n' or inChoice.lower() == u'no':
                            break
                        elif inChoice.lower() == u'y' or inChoice.lower() == u'yes':
                            changes[v] = no_Tags
                            break
                        elif inChoice.lower() == u's' or inChoice.lower() == u'skip':
                            skipped[k] = w[k]
                            break
        
        #register any artist_links so that these can be compared to existing links
        if u'skulptör_link' in w.keys() and w[u'skulptör_link']: #postponed might not have u'skulptör_link'
            for a in w[u'skulptör_link']:
                if a in linked_artists.keys(): linked_artists[a].append(w['id'])
                else: linked_artists[a] = [w['id'],]
        
        #article_links must be checked manually since link may be depictive rather than of the actual object.
        if (u'namn_link' in w.keys() and w['namn_link']) and not o[u'wiki_article']: #postponed might not have u'namn_link'
            keys=w['namn_link']
            print u'Potential title link for "%s" ("%s" on wiki)' %(o['title'], w['namn'])
            for r in range(0,len(keys)):
                key = keys[r]
                print u'%r: "%s"' %(r, keys[r])
            while True:
                inChoice=raw_input('Accept? [#/N]:')
                if inChoice == 'N' or inChoice == 'n':
                    break
                elif common.is_number(inChoice) and int(inChoice) in range(0,len(keys)):
                    #NEW START
                    name_wikidata, wdCmt = common.getWikidata(keys[int(inChoice)], verbose=True)
                    if name_wikidata:
                        changes[u'wiki_article'] = name_wikidata
                    break
        #add changes
        if changes:
            updated[w['id']] = changes.copy()
        if skipped:
            postponed[w['id']] = skipped.copy()
    #end of wiki_object loop
    

    #BUild new wikidata-module - 
    #Build odok_write-module in the same spirit. Moving lots of writeToDatabase to that
    #om inte header, try page
    #plats_link?
    return (updated, postponed, linked_artists)

def runUpdates(listFile, testing=True, queries ={}, quick=False):
    '''
    adds list data to odok
    listFile can be replaced by the postponed output
    add support for an updates_file: can read it in using fileToHits but must then break-out id 
    '''
    wiki=fileToHits(listFile)
    odok={}
    odok_result = getOdokHits(queries, odok)
    if odok_result:
        print odok_result
        exit(0)
    updated, postponed, linked_artists = updatesToDatabase(odok, wiki, quick=quick)
    
    #convert linked_artists to wikidata_id (and create if non exists)
    #compare this to odok artist_link for these id_s
    ##Note that links  might point to different artists, links may be missing or links may be missing from some but not all objects
    
    #   odokWriter.uppdateMain(conn, cursor, key, changes)
    #for key, changes in updated.iteritems():
    
    #update database
    if testing:
        f_tmp = codecs.open(u'tmpUpdates.txt','w','utf8')
        for key, changes in updated.iteritems():
            f_tmp.write('id:%s' %key)
            for k,v in changes.iteritems():
                f_tmp.write(u'|%s:%s' %(k,v))
            f_tmp.write(u'\n')
        f_tmp.close()
        f_tmp = codecs.open(u'tmpArtistLinks.txt','w','utf8')
        for artist, ids in linked_artists.iteritems():
            f_tmp.write(u'artist:%s|ids:%s\n' %(artist,';'.join(ids)))
        f_tmp.close()
    #else:
    #    commitUpdates(updated, testing=testing)
    
    #output postponed
    f_post = codecs.open(u'tmpPostponed.txt','w','utf8')
    for key, changes in postponed.iteritems():
        f_post.write('id:%s' %key)
        for k,v in changes.iteritems():
            f_post.write(u'|%s:%s' %(k,v))
        f_post.write(u'\n')
    f_post.close()

def commitUpdatesFile(filename, testing=True):
    '''
    takes the "updates" outputfile from runUpdates() and sends it to commitUpdates()
    '''
    wikiHits = fileToHits(filename)
    updates={}
    for w in wikiHits:
        idNo=w['id']
        del w['id']
        updates[idNo]=w.copy()
    
    commitUpdates(updates, testing=testing)
    print 'Done!'

def commitUpdates(updates, testing=True):
    '''
    sends the updates to the odok database
    @input: dictionary where each entry is labelled with the main_table id
            and consists of a dictionary where each entry is labeled by the relevant column
    '''
    
    #write to database
    from odokWriter import odokWriter
    odokOut = odokWriter(testing=testing)
    for key, changes in updates.iteritems():
        odokOut.uppdateTable('main', key, changes)
    odokOut.closeConnections()
    print 'Done!'

#===================Dealing with artist_links

def runArtistLinks(filename, verbose=False):
    '''
    takes the "artistLinks" outputfile from runUpdates() and analyses it
    '''
    wikiHits = fileToHits(filename)
    artists = {}
    for w in wikiHits:
        a=w['artist']
        ids = w['ids'].split(';')
        artists[a]={'ids':ids}
    
    #check which of these has a wikidata entry
    wdList=[]
    dDict = common.getWikidata(artists.keys(), verbose=verbose)
    for k, v in dDict.iteritems():
        artists[k]['wikidata'] = v
        if v: wdList.append(v)
    
    #Check for disambiguation pages and deal with pages without wikidata entries - REBUILT getWikidata/getPageInfo means this could be combined with previous
    pageList = dDict.keys()
    pageInfo={}
    common.getPageInfo(pageList, pageInfo, verbose=verbose)
    for k, v in pageInfo.iteritems():
        if 'missing' in v.keys():
            del artists[k]
        elif 'disambiguation' in v.keys() and 'redirect' in v.keys():
            artists[k]['wikidata'] = '!disambig!redirect:%s' % v['redirect']
        elif 'disambiguation' in v.keys():
            artists[k]['wikidata'] = '!disambig'
        elif 'redirect' in v.keys():
            artists[k]['wikidata'] = '!redirect=%s' % v['redirect']
        elif artists[k]['wikidata']: #a normal well behaved match
            pass
        else:
            artists[k]['wikidata'] = '!add to Wikidata'
    
    #do something to wikidata.startswith('!')
    #for the remaining check if wd matches one for an existing artist then add link to artist_links (if new)
    odokArtists(artists, wdList)
    #
    #remaining are most easily dealt with manually as one should check that wikidata entity corresponds to artist (and not someone else with similar name)
    
    #tmp
    f_tmp = codecs.open(u'tmpArtistLinks2.txt','w','utf8')
    for k, v in artists.iteritems():
        if v['ids']: #skip any that have been dealt with
            f_tmp.write(u'artist:%s|wikidata:%s|ids:%s\n' %(k,v['wikidata'],';'.join(v['ids'])))
    f_tmp.close()

def odokArtists(artistDict, wikidataList):
    '''
    checks for corresponding artists to wikidata entries.
    Returns a list of updates to be committed to artist_links
    '''
    from odokWriter import odokWriter
    odokConnection = odokWriter()
    odokResults = odokConnection.findInArtist('wiki', wikidataList)
    
    #match any that already existing
    matched = {}
    for k,v in artistDict.iteritems():
        if v['wikidata'] in odokResults.keys():
            odokId = odokResults[v['wikidata']]['id']
            v['odokId'] = odokId
            matched[str(odokId)] = v['ids'][:]
            
    #remove any links which already exist in artist_links
    odokResults = odokConnection.findArtistLinks('artist', matched.keys())
    for k,v in artistDict.iteritems():
        if 'odokId' in v.keys():
            odokId = str(v['odokId'])
            if odokId in odokResults.keys():
                odokObjs = odokResults[odokId]
                for o in odokObjs:
                    if o in v['ids']:
                        v['ids'].remove(o)
                        matched[odokId].remove(o)
    
    #add remaining matches to artist_links
    for k, vals in matched.iteritems():
        for v in vals:
            odokConnection.insertIntoTable('artist_links', {'object':v, 'artist':int(k)})
    odokConnection.closeConnections()
    
    #now remove these from artist
    for k,v in artistDict.iteritems():
        if 'odokId' in v.keys():
            odokObjs = matched[str(v['odokId'])]
            for o in odokObjs:
                if o in v['ids']:
                    v['ids'].remove(o)
    print 'Done updating artist_links!'
