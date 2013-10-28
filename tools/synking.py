#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot för att synka listor till databas:
search-and-destroy: TESTING, INCOMPLETE
'''

import dateutil.parser, codecs, datetime, ujson
import common as common
import WikiApi as wikiApi
import odok as odokConnect
import dconfig as config
import dataDicts as dataDict

def run(verbose=False):
    '''
    update database based on all list changes
    INCOMPLETE
    '''
    flog = codecs.open(u'¤syncLog.log','a','utf8')
    
    #wpApi = wikiApi.WikiApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wp_test)
    #dbApi = odokConnect.OdokApi.setUpApi(user=config.odok_user, site=config.odok_test)
    #dbReadSQL = odokConnect.OdokReader.setUp(host=config.db_test, db=config.db, user=config.db_read, passwd=config.db_read_password)
    #dbWriteSQL = odokConnect.OdokWriter.setUp(host=config.db_test, db=config.db, user=config.db_edit, passwd=config.db_edit_password)
    
    wpApi = wikiApi.WikiApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wp_site)
    dbApi = odokConnect.OdokApi.setUpApi(user=config.odok_user, site=config.odok_site)
    dbReadSQL = odokConnect.OdokReader.setUp(host=config.db_server, db=config.db, user=config.db_read, passwd=config.db_read_password)
    dbWriteSQL = odokConnect.OdokWriter.setUp(host=config.db_server, db=config.db, user=config.db_edit, passwd=config.db_edit_password)
    
    #TOBUILD lastSync = db.getSync() #timestamp of last (successful) run of this module
    lastSync = datetime.datetime.utcnow() + datetime.timedelta(days=-100) #TESTING
    thisSync = datetime.datetime.utcnow()
    flog.write(u'------START of upadates-------------\n')
    flog.write(u'last_sync: %s\nthis_sync: %s\n' %(lastSync,thisSync))
    
    
    #find changed pages
    checkList=[]
    pageList = wpApi.getEmbeddedinTimestamps(u'Mall:Offentligkonstlista', 0)
    #pageList = [{'title':u'Lista över offentlig konst i Örebro kommun', 'timestamp':str(thisSync)},] #TESTING
    for p in pageList:
        if convertTimestamp(p['timestamp'])>lastSync:
            checkList.append(p['title'])
    flog.write(u'changed pages: %r\n------------------\n' %len(checkList))
    
    checkPages = wpApi.getPage(checkList)
    
    #parse changed pages
    wiki_objects = {} #dict containing all rows/objects with an id
    for pagename, contents  in checkPages.iteritems():
        log = listToObjects(wiki_objects, pagename, contents) #adds all rows/objects with an id to the dict. Also deals with any case of same obj existing in multiple lists
        if log:
            flog.write('%s' %log)
    

    #find the corresponding odok objects
    odok_list = dbApi.getIds(wiki_objects.keys()) 
    odok_objects = {}
    for o in odok_list:
        idNo = o['id']
        if not idNo in odok_objects.keys():
            odok_objects[idNo] = o
        else:
            print 'dupe idNo for %s' %idNo
    
    #Making sure no fake/wrong id's are kicking about
    for k in wiki_objects.keys():
        if not k in odok_objects.keys():
            print u'id not found in database: %s @ %s' %(k, wiki_objects[k]['page'])

    
    #Compare
    changes = {}
    for k, o in odok_objects.iteritems():
        (diff, log) = compareToDB(wiki_objects[k],o,wpApi,dbReadSQL,verbose=verbose) #returns changelist if any otherwise NONE
        if diff:
            changes[k] = diff
        if log:
            flog.write(u'issues with %s @ %s: %s\n' %(k, wiki_objects[k]['page'], log))
    
    #update if needed
    if changes:
        #initially filter out any changes to district, cmt, artist, free, aka, address - as these are porblematic/need to be implemented differently
        not_changed = {}
        for k, v in changes.iteritems():
            not_changed[k] = {}
            if u'district' in v.keys(): not_changed[k][u'district'] = changes[k].pop(u'district')   #need to establish wiki_policy
            if u'cmt' in v.keys(): not_changed[k][u'cmt'] = changes[k].pop(u'cmt')                  #check changes
            if u'artist' in v.keys(): not_changed[k][u'artist'] = changes[k].pop(u'artist')         #need deal with multi_artist issues first
            if u'free' in v.keys(): not_changed[k][u'free'] = changes[k].pop(u'free')               #need to establish wiki_policy
            if u'aka' in v.keys(): not_changed[k][u'aka'] = changes[k].pop(u'aka')                  #separate changed_list which either crates/removes or changes an aka
            if u'address' in v.keys(): not_changed[k][u'address'] = changes[k].pop(u'address')      #need to verify quality of changes first
            if not_changed[k] == {}: del not_changed[k]
        for k, v in not_changed.iteritems():
            if changes[k] == {}: del changes[k]
        
        flog.write('changes to be done: %s\n' %ujson.encode(changes))
        flog.write('changes not to be done: %s\n' %ujson.encode(not_changed))
        
        #implement changes
        print 'committing to db' #testing
        log = commitToDatabase(dbWriteSQL, changes, verbose=verbose)
        if log:
            flog.write(u'%s\n' %log)
    else:
        flog.write('no changes to be done!\n')
    
    #TOBUILD db.setSync(thisSync) #change lastSync to thisSync
    flog.write(u'Done! Changed %r entries\n' %len(changes))
    flog.write(u'------SQL-log (read)-------------\n%s\n' %dbReadSQL.closeConnections())
    flog.write(u'------SQL-log (write)-------------\n%s\n' %dbWriteSQL.closeConnections())
    flog.write(u'------END of upadates-------------\n\n')
    flog.close()
    exit(1)
#----------------
def commitToDatabase(odokWriter, changes, verbose=False):
    '''
    Commit the changes to the database after having checked formating of paramters is correct
    '''
    log=''
    for key, v in changes.iteritems():
        diff = {}
        for param, value in v.iteritems():
            diff[param] = value['new']
            if param in [u'lat', u'lon']: #should be floats
                if diff[param]: #if not blank
                    diff[param] = float(diff[param])
            elif param == u'year':
                if diff[param]: #if not blank
                    diff[param] = int(diff[param])
        problem = odokWriter.updateTable(key, diff)
        if problem:
            log = log + 'SQL update for %s had the problem: %s\n' %(key, problem)
    #done
    return log

def listToObjects(objects, pagename, contents):
    '''
    parses a wikilist into relevant objects
    If object with same id already exists then a clash parameter is added
    Does not deal with wikitext/linking etc.
    '''
    log = ''
    
    if not contents:
        log = u'The page %s is missing or invalid\n' %pagename
        return log
    
    while(True):
        table, contents, lead_in = common.findUnit(contents, u'{{Offentligkonstlista-huvud', u'|}')
        if not table: break
        header = table[:table.find('\n')]
        table = table[len(header):]
        #read in header parameters
        headerDict = {u'län':None, u'kommun':None, u'stadsdel':None}
        parts = header.split('|')
        for p in parts:
            if '=' in p:
                pp = p.split('=')
                headerDict[pp[0].strip()]=pp[1].strip(' }')
        while(True):
            row, table, dummy = common.findUnit(table, u'{{Offentligkonstlista', u'}}', brackets={u'{{':u'}}'})
            if not row: break
            params = {u'id':'', u'id-länk':'', u'titel':'', u'aka':'', u'artikel':'', u'konstnär':'', u'konstnär2':'', u'konstnär3':'', u'konstnär4':'', u'konstnär5':'', u'årtal':'', u'beskrivning':'',
                      u'typ':'', u'material':'', u'fri':'', u'plats':'', u'inomhus':'', u'län':'', u'kommun':'', u'stadsdel':'', u'lat':'',
                      u'lon':'', u'bild':'', u'commonscat':'', u'fotnot':'', u'fotnot-namn':'', u'döljKommun':False, u'döljStadsdel':False,
                      u'page':pagename, 'clash':None, 'header':headerDict}
            boolParams = [u'döljKommun', u'döljStadsdel'] # the following should be treated as booleans
            while(True):
                part, row, dummy = common.findUnit(row, u'|', None, brackets={u'[[':u']]', u'{{':u'}}'})
                if not part: break
                if u'=' in part:
                    p=part.split(u'=')
                    for i in range(0,len(p)): p[i] = p[i].strip(' \n\t')
                    if p[0] in params.keys():
                        if p[0] in boolParams:
                            params[p[0]]=True
                        else:
                            params[p[0]]=p[1]
                    else:
                        log = log + u'Unrecognised parameter: %s = %s (%s)\n' %(p[0], p[1], pagename)
            if params['id']:
                if params['id'] in objects.keys(): #until I can deal with mulitple entries
                    objects[params['id']]['clash'] = pagename
                else:
                    objects[params['id']] = params.copy()
    if log: return log


#----------
def convertTimestamp(timestamp):
    '''
    parses ISO 8601 string to datetime then returns it without tzinfo
    '''
    timestamp = dateutil.parser.parse(timestamp) #convert from ISO 8601 format to datetime
    timestamp = timestamp.replace(tzinfo=None) #hack since datetime cannot add timezone (and mw always returns UTC)
    return timestamp

#----------
def compareToDB(wikiObj,odokObj,wpApi,dbReadSQL,verbose=False):
    '''
    compares a listobj to equiv obj in database
    this needs to deal with links and wikitext
    this should check clash parameter
    
    should return (diff, log)
            diff: dict of changes (if any) otherwise NONE
            log: list of issues encountered e.g. incorrecly formated wikitext
    TODO:
        proper log for coordinates
        only care about first X decimals in coordinte
        return needed/removed links
        fotnot-name
        should anything be done with:
            * odok:u'same_as'
            * odok:u'year_cmt'
    '''
    # wikiObj.keys() = [u'typ', u'artikel', u'titel', 'clash', u'inomhus', u'material', u'döljStadsdel', u'län', u'konstnär2', 
    #                   u'konstnär3', u'konstnär4', u'konstnär5', u'döljKommun', u'lat', u'plats', u'fotnot', u'id', u'kommun', 
    #                   u'bild', u'stadsdel', u'commonscat', u'fri', u'konstnär', u'lon', u'beskrivning', u'årtal', u'id-länk', 
    #                   u'fotnot-namn', u'aka', u'page']
    # odokObj.keys() = [u'changed', u'official_url', u'ugc', u'image', u'county', u'year', u'owner', u'commons_cat', u'id', 
    #                   u'wiki_article', u'descr', u'title', u'lon', u'source', u'same_as', u'type', u'muni', u'material', u'free', 
    #                   u'district', u'address', u'lat', u'year_cmt', u'artist', u'inside', u'created', u'cmt']
    
    log=''
    if wikiObj['clash']:
        log = log + u'clash with another page. Don\'t know how to resolve this. Skipping: %s\n' %wikiObj['clash']
        return (None, log)
    
    ##Pre-processing
    #get some more things from ODOK
    odokObj[u'linked_artists'] = dbReadSQL.findArtist(wikiObj[u'id'])
    odokObj[u'artist_links'] = []
    for a in odokObj[u'linked_artists']:
        odokObj[u'artist_links'].append(a['wiki'])
    odokObj[u'aka'] = ''
    akas = dbReadSQL.findAkas(wikiObj[u'id'])
    if akas:
        odokObj[u'aka'] = []
        for a in akas:
            odokObj[u'aka'].append(a['aka'])
        odokObj[u'aka'] = ';'.join(odokObj[u'aka'])
    if odokObj[u'wiki_article']:
        odokObj[u'wiki_article'] = odokObj[u'wiki_article'].upper()
    
    
    #the following may be inherited from the header
    if wikiObj[u'döljKommun']:
       wikiObj[u'kommun'] = wikiObj[u'header'][u'kommun']
    if not wikiObj[u'län']:
        wikiObj[u'län'] = wikiObj[u'header'][u'län']
    if wikiObj[u'döljStadsdel'] and not wikiObj[u'stadsdel']: #only overwrite non existant
       wikiObj[u'stadsdel'] = wikiObj[u'header'][u'stadsdel']
    
    #the following are limited in their values but need mapping from wiki to odok before comparison
    if wikiObj[u'fri'] == 'nej':
        wikiObj[u'fri'] = 'unfree'
    if wikiObj[u'inomhus']:
        if wikiObj[u'inomhus'] == 'ja':
            wikiObj[u'inomhus'] = 1
        elif wikiObj[u'inomhus'] == 'nej':
            wikiObj[u'inomhus'] = 0
        else:
            log = log +  'unexpected value for inside-parameter: %s\n' %wikiObj[u'inomhus']
    else:
        wikiObj[u'inomhus'] = 0
    if wikiObj[u'kommun']: #need muni code
        wikiObj[u'kommun'] = dataDict.muni_name2code[wikiObj[u'kommun']]
    if wikiObj[u'län'].startswith(u'SE-'):
        wikiObj[u'län'] = wikiObj[u'län'][len(u'SE-'):]
    if wikiObj[u'lat'] == '': wikiObj[u'lat']=None
    else: wikiObj[u'lat'] =wikiObj[u'lat'].strip('0') #due to how numbers are stored
    if wikiObj[u'lon'] == '': wikiObj[u'lon']=None
    else: wikiObj[u'lon'] =wikiObj[u'lon'].strip('0') #due to how numbers are stored
    if wikiObj[u'årtal'] == '': wikiObj[u'årtal']=None
    
        
    #Deal with artists (does not deal with order of artists being changed):
    artist_param = [u'konstnär', u'konstnär2', u'konstnär3', u'konstnär4', u'konstnär5']
    wikiObj[u'artists'] =''
    artists_links ={}
    for a in artist_param:
        if wikiObj[a]:
            (w_text, w_links) = unwiki(wikiObj[a])
            wikiObj[u'artists'] = u'%s%s;' %(wikiObj[u'artists'],w_text)
            if w_links:
                artists_links[w_text] = w_links[0]
    if wikiObj[u'artists']: wikiObj[u'artists'] = wikiObj[u'artists'][:-1] #trim trailing ;

    ##dealing with links:
    links = artists_links.values()
    if wikiObj[u'artikel']:
        links.append(wikiObj[u'artikel'])
    if links:
        links = wpApi.getPageInfo(links)
        for k,v in links.iteritems():
            if u'disambiguation' in v.keys():
                log = log + u'link to disambigpage: %s\n' %k
                links[k] = ''
            elif u'wikidata' in v.keys():
                links[k] = v[u'wikidata']
            else:
                links[k] = ''
    else:
        links = {}
    #Stick wikidata back into parameters
    if wikiObj[u'artikel']:
        wikiObj[u'artikel'] = links.pop(wikiObj[u'artikel'])
    wikiObj[u'artist_links'] = links.values()
    

    ##Main-process
    diff = {}
    #easy to compare {wiki:odok}
    trivial_params = {u'typ':u'type', u'material':u'material', u'id-länk':u'official_url', u'fri':u'free', u'inomhus':u'inside', u'årtal':u'year', u'artists':u'artist',
                      u'commonscat':u'commons_cat', u'beskrivning':u'descr', u'bild':u'image', u'titel':u'title', u'aka':u'aka', u'artikel':u'wiki_article',
                      u'plats':u'address', u'län':u'county', u'kommun':u'muni', u'stadsdel':u'district', u'lat':u'lat', u'lon':u'lon', u'fotnot':u'cmt'
                      }
    
    for k,v in trivial_params.iteritems():
        (w_text, w_links) = unwiki(wikiObj[k])
        if not (w_text == odokObj[v]):
            diff[v] = {'new':w_text, 'old':odokObj[v]}
            if verbose: print u'%s:"%s"    <--->   %s:"%s"' %(k, w_text, v, odokObj[v])
    
    
    #need to compare artist_links:
    artist_links = list(set(wikiObj[u'artist_links'])-set(odokObj[u'artist_links']))
    if artist_links and len(''.join(artist_links))>0:
        log = log + u'difference in artist links, linkdiff: %s\n' %';'.join(artist_links)
    
    ##Post-processing
    #fotnot-namn without fotnot - needs to look-up fotnot for o:cmt
    if wikiObj[u'fotnot-namn'] and not wikiObj[u'fotnot']:
        log = log + u'fotnot-namn so couldn\'t compare, fotnot-namn: %s\n' %wikiObj[u'fotnot-namn']
        if u'cmt' in diff.keys():
            del diff[u'cmt']
    
    return (diff, log)
    
    
def unwiki(wikitext):
    '''
    takes wikiformated text and returns unformated text with any links sent separately
    :parm wikitext: wikitext to be processed
    :return: (text, links)
            text: unformated text
            links: a list of any links found in the text
    '''
    if isinstance(wikitext,unicode):
        return common.extractAllLinks(wikitext, kill_tags=True)
    else:
        return wikitext, None
    