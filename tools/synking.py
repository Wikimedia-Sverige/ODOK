#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot för att synka listor till databas:
search-and-destroy: TESTING, INCOMPLETE
To do:
    Highlight wrongful formatting, missing/illegal parameter values
    Expand UGC to rewrite object correctly formatted (including any ignored parameters)
    Deal with section links (these do not have real wikidata entries)
    split run into 'generate list of pages to run on' and 'run on a given list of pages'
        that way a non-main function for runing on a given page can be introduced
'''

import dateutil.parser
import codecs
import datetime
import json
import common
import WikiApi as wikiApi
import odok as odokConnect
import dataDicts as dataDict
import UGC_synk as UGCsynk
config = common.loadJsonConfig()


def run(verbose=False, days=100, strict=True, testing=False):
    '''
    update database based on all list changes
    INCOMPLETE
    '''
    # open connections
    wpApi = wikiApi.WikiApi.setUpApi(user=config['w_username'],
                                     password=config['w_password'],
                                     site=config['wp_site'])
    wdApi = wikiApi.WikiDataApi.setUpApi(user=config['w_username'],
                                         password=config['w_password'],
                                         site=config['wd_site'])
    dbApi = odokConnect.OdokApi.setUpApi(user=config['odok_user'],
                                         site=config['odok_site'])
    dbReadSQL = odokConnect.OdokReader.setUp(host=config['db_server'],
                                             db=config['db'],
                                             user=config['db_read'],
                                             passwd=config['db_read_password'])
    dbWriteSQL = odokConnect.OdokWriter.setUp(host=config['db_server'],
                                              db=config['db'],
                                              user=config['db_edit'],
                                              passwd=config['db_edit_password'],
                                              testing=testing)

    # set up logging
    logfile = u'¤syncLog.log'
    # TOBUILD lastSync = db.getLastSync(logfile) #timestamp of last (successful) run of this module

    lastSync = datetime.datetime.utcnow() + datetime.timedelta(days=-days)  # TESTING
    print u'Checking changes since %s' % lastSync
    flog = codecs.open(logfile, 'a', 'utf8')
    thisSync = datetime.datetime.utcnow()
    flog.write(u'------START of updates-------------\n')
    flog.write(u'last_sync: %s\nthis_sync: %s\n' % (lastSync, thisSync))

    # find changed pages
    checkList = []
    pageList = wpApi.getEmbeddedinTimestamps(u'Mall:Offentligkonstlista', 0)
    for p in pageList:
        if strict and not p['title'].startswith(u'Lista över'):
            continue
        if convertTimestamp(p['timestamp']) > lastSync:
            checkList.append(p['title'])
    flog.write(u'changed pages: %r\n------------------\n' % len(checkList))

    # stop if nothing to check
    if len(checkList) == 0:
        print u'Found no changed pages.'
        exit(1)

    # check if all list pages have a wikidataID, if not then create one
    claims = {'P31': 'Q13406463', 'P360': 'Q557141'}  # list of public art
    pageInfos = wpApi.getPageInfo(checkList)
    for pagename, pageinfo in pageInfos.iteritems():
        if 'wikidata' not in pageinfo.keys() or pageinfo['wikidata'] == '':
            newId = wdApi.makeEntity(pagename, site='svwiki', lang='sv',
                                     label=pagename, claims=claims)
            pageInfos[pagename]['wikidata'] = newId

    # deal with new UGC items
    (log, newUGC) = UGCsynk.run(checkList, pageInfos, wpApi, dbWriteSQL)
    flog.write(u'\n---------- New UGC items (%r): --------\n' % newUGC)
    if log:
        flog.write('%s\n' % log)

    # read pages (after UGC updates)
    checkPages = wpApi.getPage(checkList)

    # parse changed pages
    print u'%r pages to parse...' % len(checkPages)
    wiki_objects = {}  # dict containing all rows/objects with an id
    for pagename, contents in checkPages.iteritems():
        # add all rows/objects with an id to the dict and deal with any case of same obj existing in multiple lists
        log = listToObjects(wiki_objects, pagename, pageInfos[pagename]['wikidata'], contents)
        if log:
            flog.write('%s' % log)

    print u'Parsed all pages and found %r objects. Looking for corresponding objects in database...' % len(wiki_objects)
    # find the corresponding odok objects
    odok_list = dbApi.getIds(wiki_objects.keys())
    odok_objects = {}
    for o in odok_list:
        idNo = o['id']
        if idNo not in odok_objects.keys():
            odok_objects[idNo] = o
        else:
            print 'dupe idNo for %s' % idNo

    # Making sure no fake/wrong id's are kicking about
    for k in wiki_objects.keys():
        if k not in odok_objects.keys():
            print u'id not found in database: %s @ %s' % (k, wiki_objects[k]['page'])

    print u'Looked in database and found %r corresponding objects. Starting comparison.' % len(odok_objects)
    flog.write(u'issues:\n')
    # Compare
    counter = 0
    changes = {}
    for k, o in odok_objects.iteritems():
        counter += 1
        (diff, log) = compareToDB(wiki_objects[k], o, wpApi, dbReadSQL, verbose=verbose)  # returns changelist if any otherwise NONE
        if diff:
            changes[k] = diff
        if log:
            flog.write(u'%s @ %s: %s' % (k, wiki_objects[k]['page'], log))
        if counter % 100 == 0:
            print u'%r/%r' % (counter, len(odok_objects))
    flog.write(u'\n')  # end of issues

    print u'Found %r changed objects. Sorting...' % len(changes)
    # update if needed
    if changes:
        ccounter = 0
        ncounter = 0
        # initially filter out any changes to cmt, artist, free, aka, address - as these are problematic/need to be implemented differently
        not_changed = {}
        for k, v in changes.iteritems():
            not_changed[k] = {}
            if u'cmt' in v.keys():  # check changes, problem with multiple footnotes and some made with templates
                not_changed[k][u'cmt'] = changes[k].pop(u'cmt')
            if u'free' in v.keys():  # need to establish wiki_policy+need to enable synk db->wiki as this is set by updateCopyright
                not_changed[k][u'free'] = changes[k].pop(u'free')
            if u'image' in v.keys():  # temporarilly added due to BUS
                not_changed[k][u'image'] = changes[k].pop(u'image')

            if not_changed[k] == {}:
                del not_changed[k]
            else:
                ncounter += len(not_changed[k].keys())

            ccounter += len(changes[k].keys())
        for k, v in not_changed.iteritems():
            if changes[k] == {}:
                del changes[k]

        flog.write('changes to be done (%r): %s\n' % (ccounter, json.dumps(changes)))
        flog.write('changes not to be done (%r): %s\n' % (ncounter, json.dumps(not_changed)))

        # implement changes
        print 'Committing %r of these to SQL db' % ccounter  # testing
        log = commitToDatabase(dbWriteSQL, changes, verbose=verbose)
        if log:
            flog.write(u'%s\n' % log)
    else:
        flog.write('no changes to be done!\n')
    flog.write(u'Done! Changed %r entries\n' % len(changes))

    # Identify any removed objects
    log = removedObjects(dbApi, dbWriteSQL, pageInfos, wiki_objects)
    if log:
        flog.write(u'%s\n' % log)

    # Identify any removed lists
    log = removedLists(dbApi, wpApi, dbWriteSQL, pageList, pageInfos)
    if log:
        flog.write(u'%s\n' % log)

    # TOBUILD db.setSync(thisSync) #change lastSync to thisSync
    flog.write(u'------SQL-log (read)-------------\n%s\n' % dbReadSQL.closeConnections())
    flog.write(u'------SQL-log (write)-------------\n%s\n' % dbWriteSQL.closeConnections())
    flog.write(u'------END of updates-------------\n\n')
    flog.close()
    # TOBUILD db.makeDump() #change create a dump (ideally one which is incremental)
    print 'Done, woho!'


def removedObjects(dbApi, odokWriter, pageInfos, wiki_objects):
    '''
    Identify if any objects have been removed from the list and,
    if so empty their list field in db.
    TODO: explain params
    '''
    log = ''
    # identify wikidata ids of modified pages
    listIds = []
    for k, v in pageInfos.iteritems():
        listIds.append(v['wikidata'])

    # get all members of these, according to db
    listmembers = dbApi.getListMembers(listIds, show=[u'id', u'list'])

    # identify any removed
    removedList = []
    for k in listmembers:
        if k[u'id'] not in wiki_objects.keys():
            removedList.append(k[u'id'])

    # update in db
    # UPDATE `main_table` SET `list` = '' where id in (removeList)
    for key in removedList:
        problem = odokWriter.updateTable(key, {'list': ''})
        if problem:
            log += 'SQL update for %s had the problem: %s\n' % (key, problem)
    # done
    print u'Removed %r objects from lists\n' % len(removedList)
    return log


def removedLists(dbApi, wpApi, odokWriter, pageList, oldPageInfos):
    '''
    Identify if any objects have been removed from the list and,
    if so empty their list field in db.
    :param pageList: all pages in main namespace with the right template
    :param oldPageInfos: pageInfo but only for updated pages \
                         (usefull for retrieving newly added wikidataIds)
    '''
    log = ''

    # extract pagenames
    checkList = []
    for p in pageList:
        checkList.append(p['title'])

    # get wikidata id
    pageInfos = wpApi.getPageInfo(checkList)
    wpList = []
    for pagename, pageinfo in pageInfos.iteritems():
        if 'wikidata' not in pageinfo.keys() or pageinfo['wikidata'] == '':
            # this may occur if wikidata lable was added during synk but this has yet to show up on-wiki
            if pagename in oldPageInfos.keys():
                wpList.append(oldPageInfos[pagename]['wikidata'])
            else:
                log += 'Deleted lists: No wikidata for list "%s", aborting!' % pagename
                return log
        else:
            wpList.append(pageinfo['wikidata'])

    # identify any removed
    removedList = []
    dbLists = dbApi.getAllLists()
    for k in dbLists:
        if k not in wpList:
            removedList.append(k)

    # update in db
    # UPDATE `main_table` SET `list` = '' WHERE `list` IN removeList
    if len(removedList) > 0:
        problem = odokWriter.clearListEntries(removedList)
        if problem:
            log += 'SQL update for clearList had the problem: %s\n' % problem
        print u'The following lists were deleted: %s\n' % ', '.join(removedList)

    # done
    return log


def commitToDatabase(odokWriter, changes, verbose=False):
    '''
    Commit the changes to the database after having checked formating of paramters is correct
    '''
    log = ''
    for key, v in changes.iteritems():
        diff = {}
        for param, value in v.iteritems():
            diff[param] = value['new']
            if param in [u'lat', u'lon']:  # should be floats
                if diff[param]:  # if not blank
                    diff[param] = float(diff[param])
            elif param == u'year':
                if diff[param]:  # if not blank
                    diff[param] = int(diff[param])
            elif param == u'artist_links':
                # handle here then remove from diff
                values = []
                for v in diff[param]:
                    values.append({u'object': key, u'artist': v})
                problem = odokWriter.insertIntoTable('artist_links', values)
                if problem:
                    log += 'SQL update for %s had the problem: %s\n' % (key, problem)
                del(diff[param])
            elif param == u'aka_list':
                # handle here then remove from diff
                values = []
                for v in diff[param]:
                    values.append({u'main_id': key, u'title': v})  # id is autoincremented
                problem = odokWriter.insertIntoTable('aka', values)
                if problem:
                    log += 'SQL update for %s had the problem: %s\n' % (key, problem)
                del(diff[param])

        if len(diff.keys()) > 0:
            problem = odokWriter.updateTable(key, diff)
            if problem:
                log += 'SQL update for %s had the problem: %s\n' % (key, problem)
    # done
    return log


def listToObjects(objects, pagename, list_wd, contents):
    '''
    parses a wikilist into relevant objects
    If object with same id already exists then a clash parameter is added
    Does not deal with wikitext/linking etc.
    '''
    log = ''

    if not contents:
        log = u'The page %s is missing or invalid\n' % pagename
        return log

    # the following should be treated as booleans
    boolParams = [u'döljKommun', u'döljStadsdel', u'tidigare', u'visaId']

    while(True):
        table, contents, lead_in = common.findUnit(contents, u'{{Offentligkonstlista-huvud', u'|}')
        if not table:
            break
        header = table[:table.find('\n')]
        table = table[len(header):]

        # read in header parameters
        headerDict = {u'län': None, u'kommun': None, u'stadsdel': None,
                      u'tidigare': None, u'visaId': None}
        parts = header.split('|')
        for p in parts:
            if '=' in p:
                pp = p.split('=')
                for i in range(0, len(pp)):
                    pp[i] = pp[i].strip(' \n\t}')
                if pp[0] in headerDict.keys():
                    if pp[0] in boolParams:
                        headerDict[pp[0]] = True
                    else:
                        headerDict[pp[0]] = pp[1]
                else:
                    log += u'Unrecognised header parameter: %s = %s (%s)\n' % (pp[0], pp[1], pagename)

        while(True):
            row, table, dummy = common.findUnit(table, u'{{Offentligkonstlista', u'}}', brackets={u'{{': u'}}'})
            if not row:
                break
            params = {
                u'id': '',
                u'id-länk': '',
                u'titel': '',
                u'aka': '',
                u'artikel': '',
                u'konstnär': '',
                u'konstnär2': '',
                u'konstnär3': '',
                u'konstnär4': '',
                u'konstnär5': '',
                u'konstnär6': '',
                u'konstnär7': '',
                u'konstnär8': '',
                u'konstnär9': '',
                u'årtal': '',
                u'beskrivning': '',
                u'typ': '',
                u'material': '',
                u'fri': '',
                u'plats': '',
                u'inomhus': '',
                u'län': '',
                u'kommun': '',
                u'stadsdel': '',
                u'lat': '',
                u'lon': '',
                u'bild': '',
                u'commonscat': '',
                u'fotnot': '',
                u'fotnot-namn': '',
                u'döljKommun': False,
                u'döljStadsdel': False,
                u'visaId': False,
                u'fotnot2': '',
                u'fotnot2-namn': '',
                u'fotnot3': '',
                u'fotnot3-namn': '',
                u'page': pagename,
                u'list': list_wd,
                'clash': None,
                'header': headerDict}

            while(True):
                part, row, dummy = common.findUnit(row, u'|', None, brackets={u'[[': u']]', u'{{': u'}}'})
                if not part:
                    break
                if u'=' in part:
                    p = part.split(u'=')
                    p = [p[0], part[len(p[0])+1:]]  # to avoid problems with = signs in urls etc.
                    for i in range(0, len(p)):
                        p[i] = p[i].strip(' \n\t')
                    if p[0] in params.keys():
                        if p[0] in boolParams:
                            params[p[0]] = True
                        else:
                            params[p[0]] = p[1]
                    else:
                        log += u'Unrecognised parameter: %s = %s (%s)\n' % (p[0], p[1], pagename)
            if params['id']:
                if params['id'] in objects.keys():  # until I can deal with mulitple entries
                    objects[params['id']]['clash'] = pagename
                else:
                    objects[params['id']] = params.copy()
    if log:
        return log


# ----------
def convertTimestamp(timestamp):
    '''
    parses ISO 8601 string to datetime then returns it without tzinfo
    '''
    timestamp = dateutil.parser.parse(timestamp)  # convert from ISO 8601 format to datetime
    timestamp = timestamp.replace(tzinfo=None)  # hack since datetime cannot add timezone (and mw always returns UTC)
    return timestamp


def compareToDB(wikiObj, odokObj, wpApi, dbReadSQL, verbose=False):
    '''
    compares a listobj to equiv obj in database
    this needs to deal with links and wikitext
    this should check clash parameter

    should return (diff, log)
            diff: dict of changes (if any) otherwise NONE
            log: list of issues encountered e.g. incorrecly formated wikitext
    TODO:
        proper log for coordinates
        only care about first X decimals in coordinate
        return needed/removed links
        fotnot-name
        should anything be done with:
            * odok:u'same_as'
            * odok:u'year_cmt'
    '''
    # wikiObj.keys() = [u'typ', u'artikel', u'titel', 'clash', u'inomhus', u'material', u'döljStadsdel', u'län', u'konstnär2',
    #                   u'konstnär3', u'konstnär4', u'konstnär5', u'konstnär6', u'konstnär7', u'konstnär8', u'konstnär9',
    #                   u'döljKommun', u'lat', u'plats', u'fotnot', u'fotnot2', u'fotnot3', u'id', u'kommun',
    #                   u'bild', u'stadsdel', u'commonscat', u'fri', u'konstnär', u'lon', u'beskrivning', u'årtal', u'id-länk',
    #                   u'fotnot-namn', u'fotnot2-namn', u'fotnot3-namn', u'aka', u'page', u'lista', u'header']
    # odokObj.keys() = [u'changed', u'official_url', u'ugc', u'image', u'county', u'year', u'owner', u'commons_cat', u'id',
    #                   u'wiki', u'list', u'descr', u'title', u'lon', u'source', u'same_as', u'type', u'muni', u'material', u'free',
    #                   u'district', u'address', u'lat', u'year_cmt', u'artist', u'inside', u'created', u'cmt', u'removed']

    log = ''
    if wikiObj['clash']:
        log += u'clash with another page. Don\'t know how to resolve this. Skipping: %s\n' % wikiObj['clash']
        return (None, log)

    ## Pre-processing
    # get some more things from ODOK
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
    if odokObj[u'wiki']:
        odokObj[u'wiki'] = odokObj[u'wiki'].upper()

    # the following is inherited from the header
    if wikiObj[u'header'][u'tidigare']:
        wikiObj[u'tidigare'] = 1
    else:
        wikiObj[u'tidigare'] = 0

    # the following may be inherited from the header
    if wikiObj[u'döljKommun']:
        wikiObj[u'kommun'] = wikiObj[u'header'][u'kommun']
    if not wikiObj[u'län']:
        wikiObj[u'län'] = wikiObj[u'header'][u'län']
    if wikiObj[u'döljStadsdel'] and not wikiObj[u'stadsdel']:  # only overwrite non existant
        wikiObj[u'stadsdel'] = wikiObj[u'header'][u'stadsdel']
    # the following are limited in their values but need mapping from wiki to odok before comparison
    if wikiObj[u'fri'].lower() == 'nej':
        wikiObj[u'fri'] = 'unfree'
    if wikiObj[u'inomhus']:
        if wikiObj[u'inomhus'].lower() == 'ja':
            wikiObj[u'inomhus'] = 1
        elif wikiObj[u'inomhus'].lower() == 'nej':
            wikiObj[u'inomhus'] = 0
        else:
            log += 'unexpected value for inside-parameter (defaulting to no): %s\n' % wikiObj[u'inomhus']
            wikiObj[u'inomhus'] = 0
    else:
        wikiObj[u'inomhus'] = 0
    if wikiObj[u'kommun']:  # need muni code
        wikiObj[u'kommun'] = dataDict.muni_name2code[wikiObj[u'kommun']]
    if wikiObj[u'län'].startswith(u'SE-'):
        wikiObj[u'län'] = wikiObj[u'län'][len(u'SE-'):]
    if wikiObj[u'lat'] == '':
        wikiObj[u'lat'] = None
    else:
        if len(wikiObj[u'lat']) > 16:
            wikiObj[u'lat'] = '%.13f' % float(wikiObj[u'lat'])
        wikiObj[u'lat'] = wikiObj[u'lat'].strip('0')  # due to how numbers are stored
    if wikiObj[u'lon'] == '':
        wikiObj[u'lon'] = None
    else:
        if len(wikiObj[u'lon']) > 16:
            wikiObj[u'lon'] = '%.13f' % float(wikiObj[u'lon'])
        wikiObj[u'lon'] = wikiObj[u'lon'].strip('0')  # due to how numbers are stored
    if wikiObj[u'årtal'] == '':
        wikiObj[u'årtal'] = None

    # Deal with artists (does not deal with order of artists being changed):
    artist_param = [u'konstnär', u'konstnär2', u'konstnär3',
                    u'konstnär4', u'konstnär5', u'konstnär6',
                    u'konstnär7', u'konstnär8', u'konstnär9']
    wikiObj[u'artists'] = ''
    artists_links = {}
    for a in artist_param:
        if wikiObj[a]:
            (w_text, w_links) = unwiki(wikiObj[a])
            wikiObj[u'artists'] = u'%s%s;' % (wikiObj[u'artists'], w_text)
            if w_links:
                artists_links[w_text] = w_links[0]
    if wikiObj[u'artists']:
        wikiObj[u'artists'] = wikiObj[u'artists'][:-1]  # trim trailing ;

    ## dealing with links:
    links = artists_links.values()
    if wikiObj[u'artikel']:
        if u'#' in wikiObj[u'artikel']:
            log += u'link to section: %s\n' % wikiObj[u'artikel']
        else:
            links.append(wikiObj[u'artikel'])
    if links:
        links = wpApi.getPageInfo(links)
        for k, v in links.iteritems():
            if u'disambiguation' in v.keys():
                log += u'link to disambigpage: %s\n' % k
                links[k] = ''
            elif u'wikidata' in v.keys():
                links[k] = v[u'wikidata']
            else:
                links[k] = ''
    else:
        links = {}
    # Stick wikidata back into parameters
    if wikiObj[u'artikel']:
        if u'#' not in wikiObj[u'artikel']:
            wikiObj[u'artikel'] = links.pop(wikiObj[u'artikel'])
        else:
            wikiObj[u'artikel'] = ''
    wikiObj[u'artist_links'] = links.values()

    ## Main-process
    diff = {}
    # easy to compare {wiki:odok}
    trivial_params = {u'typ': u'type',
                      u'material': u'material',
                      u'id-länk': u'official_url',
                      u'fri': u'free',
                      u'inomhus': u'inside',
                      u'artists': u'artist',
                      u'årtal': u'year',
                      u'commonscat': u'commons_cat',
                      u'beskrivning': u'descr',
                      u'bild': u'image',
                      u'titel': u'title',
                      u'aka': u'aka',
                      u'artikel': u'wiki',
                      u'list': u'list',
                      u'plats': u'address',
                      u'län': u'county',
                      u'kommun': u'muni',
                      u'stadsdel': u'district',
                      u'tidigare': u'removed',
                      u'lat': u'lat',
                      u'lon': u'lon',
                      u'fotnot': u'cmt'}

    for k, v in trivial_params.iteritems():
        (w_text, w_links) = unwiki(wikiObj[k])
        if not (w_text == odokObj[v]):
            diff[v] = {'new': w_text, 'old': odokObj[v]}
            if verbose:
                print u'%s:"%s"    <--->   %s:"%s"' % (k, w_text, v, odokObj[v])

    ## Needing separate treatment
    # comparing artist_links: u'artist_links':u'artist_links'
    artist_diff = {'+': [], '-': []}
    artist_links = list(set(wikiObj[u'artist_links'])-set(odokObj[u'artist_links']))
    if artist_links and len(''.join(artist_links)) > 0:
        artist_diff['+'] = artist_links[:]  # slice to clone the list
    artist_links = list(set(odokObj[u'artist_links'])-set(wikiObj[u'artist_links']))
    if artist_links and len(''.join(artist_links)) > 0:
        artist_diff['-'] = artist_links[:]  # slice to clone the list
    # handler can only deal with new artists
    if len(artist_diff['-']) == 0 and len(artist_diff['+']) > 0:
        artIds = dbReadSQL.getArtistByWiki(artist_diff['+'])  # list of id:{'first_name', 'last_name', 'wiki', 'birth_date', 'death_date', 'birth_year', 'death_year'}
        newArtistLinks = []
        for k, v in artIds.iteritems():
            artist_diff['+'].remove(v['wiki'])
            newArtistLinks.append(k)
        if len(newArtistLinks) > 0:
            diff[u'artist_links'] = {'new': newArtistLinks, 'old': []}
    # output remaining to log
    for k, v in artist_diff.iteritems():
        if len(v) > 0:
            log += u'difference in artist links, linkdiff%s: %s\n' % (k, ';'.join(v))

    ## akas
    if 'aka' not in diff.keys():
        pass
    elif sorted(diff['aka']['new'].split(';')) == sorted(diff['aka']['old'].split(';')):
        del(diff['aka'])
    else:
        aka_diff = {'+': [], '-': []}
        aka_list = list(set(diff['aka']['new'].split(';'))-set(diff['aka']['old'].split(';')))
        if aka_list and len(''.join(aka_list)) > 0:
            aka_diff['+'] = aka_list[:]  # slice to clone the list
        aka_list = list(set(diff['aka']['old'].split(';'))-set(diff['aka']['new'].split(';')))
        if aka_list and len(''.join(aka_list)) > 0:
            aka_diff['-'] = aka_list[:]  # slice to clone the list
        # handler can only deal with new akas
        if len(aka_diff['-']) == 0 and len(aka_diff['+']) > 0:
            diff[u'aka_list'] = {'new': aka_diff['+'], 'old': []}
            del(aka_diff['+'])
        # output remaining to log
        for k, v in aka_diff.iteritems():
            if len(v) > 0:
                log += u'difference in akas, diff%s: %s\n' % (k, ';'.join(v))
        # remove these for now
        del(diff['aka'])

    ## Post-processing
    # fotnot-namn without fotnot - needs to look-up fotnot for o:cmt
    if wikiObj[u'fotnot-namn'] and not wikiObj[u'fotnot']:
        log += u'fotnot-namn so couldn\'t compare, fotnot-namn: %s\n' % wikiObj[u'fotnot-namn']
        if u'cmt' in diff.keys():
            del diff[u'cmt']

    # free defaults to unfree in wiki but not necessarily in db
    if 'free' in diff.keys() and diff['free']['new'] == '':
        if diff['free']['old'] == 'unfree':
            diff.pop('free')

    # Years which are not plain numbers cannot be sent to db
    if 'year' in diff.keys():
        if not common.is_int(diff['year']['new']):
            year = diff.pop('year')
            log += u'Non-integer year: %s\n' % year['new']

    # lat/lon reqires an extra touch as only decimal numbers and nones may be sent to db
    if 'lat' in diff.keys():
        if not diff['lat']['new']:
            # if new = None
            pass
        elif not common.is_number(diff['lat']['new']):
            lat = diff.pop('lat')
            log += u'Non-decimal lat: %s\n' % lat['new']
    if 'lon' in diff.keys():
        if not diff['lon']['new']:
            pass
        elif not common.is_number(diff['lon']['new']):
            lat = diff.pop('lon')
            log += u'Non-decimal lon: %s\n' % diff['lon']['new']

    # Basic validation of artist field:
    if 'artist' in diff.keys():
        # check that number of artists is the same
        if '[' in diff['artist']['old']:
            artist = diff.pop('artist')
            log += u'cannot deal with artists which include group affilitations: %s --> %s\n' % (artist['old'], artist['new'])
        elif (len(diff['artist']['old'].split(';')) != len(diff['artist']['new'].split(';'))) and (len(diff['artist']['old']) > 0):
            # if not the same number when there were originally some artists
            artist = diff.pop('artist')
            log += u'difference in number of artists: %s --> %s\n' % (artist['old'], artist['new'])

    # Unstripped refrences
    for k in diff.keys():
        if k in (u'official_url', u'inside', u'removed'):  # not strings or ok to have http
            continue
        if diff[k]['new'] and 'http' in diff[k]['new']:
            val = diff.pop(k)
            log += u'new value for %s seems to include a url: %s --> %s\n' % (k, val['old'], val['new'])

    return (diff, log)


def unwiki(wikitext):
    '''
    takes wikiformated text and returns unformated text with any links sent separately
    :parm wikitext: wikitext to be processed
    :return: (text, links)
            text: unformated text
            links: a list of any links found in the text
    '''
    if isinstance(wikitext, unicode):
        return common.extractAllLinks(wikitext, kill_tags=True)
    else:
        return wikitext, None


if __name__ == "__main__":
    import sys
    usage = '''Usage: python synking.py days
\tdays(optional): number of days back to search for changes (default 100)'''
    argv = sys.argv[1:]
    if len(argv) == 0:
        run()
    elif len(argv) == 1:
        if common.is_int(argv[0]):
            days = int(argv[0])
            print 'running for %d days' % days
            run(days=days)
        else:
            print usage
    else:
        print usage
# EoF
