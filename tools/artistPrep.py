# -*- coding: UTF-8  -*-
#
# A module to facilitate the importing of new artists from municipal data
#
# Usage:
#   Run fileWithWikidata for your csv file
#   View -tmp2.txt at the relevant wikipedia to manually fix any disambiguations and to verify that the articles are about the right person
#   Enter these corrections into -tmp.txt
#   run openCSV(u'...-tmp.txt', prefix=u'...')
#   run ...-artists.sql in sql
#   ...
#
# Known Bugs:
# if artist and a group colaborate then this ignors the single artist
#       i.e. groupName [memberA;memberB];singleA -> memberA;memberB (should give memberA;memberB:singleA)
#
import codecs
import common as common
import WikiApi as wikiApi
import odok as odokConnect
import dconfig as config

def makeSource(source):
    '''
    Given that a correctly formated file exists at source.csv this
    parses the file to create a sql file for adding the source to the database
    '''
    f = codecs.open(u'%s.csv' % source, 'r', 'utf8')
    lines = f.read().split('\n')
    f.close()
    f = codecs.open(u'%s-source.sql' % source, 'w', 'utf8')
    d = {'id':None, 'name':None, 'wiki':None, 'real_id':None, 'url':None, 'cmt':None}
    for l in lines:
        if len(l) == 0 or not l.startswith('#') or l.startswith('##'):
            continue
        label = l[1:].split(':')[0].strip().lower()
        if label in d.keys():
            d[label] = l[l.find(':')+1:].strip()

    f.write("""INSERT INTO `source_table`(`id`, `name`, `wiki`, `real_id`, `url`, `cmt`)
VALUES ("%s","%s","%s",%d,"%s","%s");""" % (d['id'], d['name'], d['wiki'], int(d['real_id']), d['url'], d['cmt']))
    f.close()

def fileWithWikidata(filename=u'Artists.csv', idcol=0, namecol=[4,3], verbose=False):
    '''
    Given a csv file containing object ids and artist names this checks for matching pages on a wikipedia.
    This can either be a csv file with one line per item or with one line per artist and idnos semicolonseparated
    If the page exists but does not contain a wikidata_item then one is created.
    It returns two files:
    *-tmp.txt  which contains artistnames with mapped wikidata items and any comments
    *-tmp2.txt which contains wikicode of the above
    '''
    wpApi = wikiApi.WikiApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wp_site, verbose=verbose)
    wdApi = wikiApi.WikiDataApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wd_site, verbose=verbose)
    dbReadSQL = odokConnect.OdokReader.setUp(host=config.db_server, db=config.db, user=config.db_read, passwd=config.db_read_password)
    outfile = filename[:-4]

    aDict=file_to_dict(filename=filename, idcol=idcol, namecol=namecol, verbose=verbose)
    if '' in aDict.keys(): #remove any artistless entries (these cause issues with wikidata)
        del aDict['']
    wDict = wpApi.getPageInfo(aDict.keys(), debug=verbose)

    wdList =[]
    for k,v in aDict.iteritems():
        #separate wikidata from other pageinfo
        wd=''
        info = wDict[k[:1].upper()+k[1:]] #wp article must start with capital letter
        if 'wikidata' in info.keys():
            wd = info['wikidata']
            del info['wikidata']
        elif not 'missing' in info.keys():
            #If page exists but without a wikidata entry then create a new wikidata entry and return that id (also deals with Bug 54882)
            wdNew = wdApi.makeEntity(k, site=u'svwiki')
            if wdNew:
                wd = wdNew
        if len(info)==0:
            info=''
        if wd:
            wdList.append(wd)
        #check ODOK for matches (so that these won't have to be checked manually)
        aDict[k] = [v[0], v[1], wd, info, '']
    if wdList:
        wikidataFromOdok(wdList, aDict, dbReadSQL)
    makeCSV(aDict, '%s-tmp.txt' % outfile)
    makeWiki(aDict, '%s-tmp2.txt' % outfile)
#
def artistFromLog(filename='artist-dump.csv', idcol=0, namecol=3, verbose=False):
    wpApi = wikiApi.WikiApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wp_site, verbose=verbose)
    wdApi = wikiApi.WikiDataApi.setUpApi(user=config.w_username, password=config.w_password, site=config.wd_site, verbose=verbose)
    wdDict = wdApi.getArticles(aDict.keys())
    dbReadSQL = odokConnect.OdokReader.setUp(host=config.db_server, db=config.db, user=config.db_read, passwd=config.db_read_password)
    outfile = filename[:-4]

    aDict=file_to_dict(filename=filename, idcol=idcol, namecol=namecol, verbose=verbose)
    #aDict is now wd:([ids],wd)

    for k, v in wdDict.iteritems():
        a = aDict.pop(k)
        aDict[v['title']] = a
    #aDict is now wp:([ids],wd)

    wpDict = wpApi.getPageInfo(aDict.keys(), debug=verbose)

    for k,v in aDict.iteritems():
        info = wpDict[k[:1].upper()+k[1:]] #wp article must start with capital letter
        del info['wikidata']
        if len(info)==0:
            info=''
        name = ';'.join(k.split(' '))
        aDict[k] = [v[0], name, v[1], info, '']
    wikidataFromOdok(wdDict.keys(), aDict, dbReadSQL)

    makeCSV(aDict, '%s-tmp.txt' % outfile)
    makeWiki(aDict, '%s-tmp2.txt' % outfile)
    #Check file as normal + for name formating then openCSV(u'%s-tmp.txt'%outfile, prefix=u'')
#
def wikidataFromOdok(wdList, aDict, dbReadSQL):
    '''
    Checks a list of wikidata entities against hits in the ODOK database
    '''
    response = dbReadSQL.getArtistByWiki(wdList)

    #resonse is a list of odok_ids with wd info, change to become a list of wd_ids with odok_info
    #then add these to aDict
    if response:
        wdList = {}
        for k, v in response.iteritems():
            wdList[v['wiki'].upper()] = k
        for k, v in aDict.iteritems():
            if v[2] and v[2] in wdList.keys():
                v[4] = wdList[v[2]]
#
def makeCSV(dDict, filename):
    f = codecs.open(filename,'w','utf8')
    for k, v in dDict.iteritems():
        f.write(u'%s|%s|%s|%s|%s|%s\n' %(k,';'.join(v[0]),v[1],v[2],v[3],v[4]))
    f.close()
    print u'%s created' %filename
#
def makeWiki(dDict, filename):
    f = codecs.open(filename,'w','utf8')
    f.write(u'{| class="wikitable sortable" style="width:100%; font-size:89%; margin-top:0.5em;"\n|-\n!namn!!objekt!!förnamn;efternamn||wikidata||comment||odok match\n|-\n')
    rows = []
    for k, v in dDict.iteritems():
        rows.append(u'|[[%s]]||%s||%s||%s||%s||%s' %(k,';'.join(v[0]),v[1],v[2],v[3],v[4]))
    f.write('\n|-\n'.join(rows))
    f.write(u'\n|}\n')
    f.close()
    print u'%s created' %filename

def openCSV(filename, prefix=''):
    '''
    prefix is needed in case idno don't already include source
    This is not live (outputs to local file)
    !!!BROKEN!!! needs to deal with added info i.e. will likely recieve a dict
    '''
    outName = u'%s-artists.sql' %filename.replace(u'-tmp','')[:-4]
    f = codecs.open(outName,'w','utf8')
    lines = common.openFile(filename)
    for l in lines:
        cols = l.split('|')
        ids = cols[1].split(';')
        for i in range(0,len(ids)): ids[i] = u'%s%s' %(prefix, ids[i])
        if len(cols[2].split(';'))==2:
            fName, lName = cols[2].split(';')
        elif len(cols[2].split(';'))==1:
            lName = cols[2]
            fName = ''
        else:
            print u'Aborting: name column had to many parts for: %s' %l
            break
        wikidata = cols[3]
        comments = cols[4]
        inOdok = cols[5]
        if len(wikidata)>0 and not inOdok:
            f.write(addArtist(fName, lName, wikidata, ids))
            f.write('\n')
        elif inOdok:
            f.write(addLink(inOdok, ids))
            f.write('\n')
            #add to artist_links
    f.close()
    print 'created %s'%outName

def addArtist(fName, lName, wikidata, ids):
    #check if it exists already
    query = u'INSERT INTO artist_table (first_name, last_name, wiki) VALUES ("%s","%s","%s"); ' %(fName, lName, wikidata)
    query = u'%s\nSET @last_artist_id = LAST_INSERT_ID();' %query
    for i in ids:
        query = u'%s\nINSERT INTO artist_links (object,artist) VALUES ("%s", @last_artist_id); ' %(query,i)
    return u'%s\n' %query

def addLink(artist, ids):
    #check if it exists already
    query = u'INSERT INTO artist_links (object,artist) VALUES'
    for i in ids:
        query = u'%s\n("%s",%s),' %(query,i,artist)
    return u'%s;\n' % query[:-1]

def file_to_dict(filename, idcol=0, namecol=1, verbose=False):
    '''
    reads in a file and passes it to a dict where each row is in turn a dict
    lines starting with # are treated as comments. Semicolons in the namecol are treated as separate names.
    Sqare brakets as the real value (i.e. rest is ignored)
    '''
    listcols = isinstance(namecol,list)
    if listcols and len(namecol) != 2:
        print u'namecol must be a single integer or two integers'
    lines = common.openFile(filename)
    dDict = {}
    for l in lines:
        if len(l)==0 or l.startswith(u'#'):
            continue
        col = l.split('|')
        idno = col[idcol]
        nameparts={}
        #names can be constructed by two columns (first name, last name)
        if listcols: #
            namesF = common.extractName(col[namecol[0]])
            namesL = common.extractName(col[namecol[1]])
            names=[]
            for i in range(0,len(namesF)):
                name = u'%s %s' % (namesF[i],namesL[i])
                names.append(name.strip())
                nameparts[name.strip()] = u'%s;%s' %(namesF[i],namesL[i])
        else:
            names = common.extractName(col[namecol])
            #trying to identify the name parts
            for name in names:
                nameparts[name] = common.extractNameParts(name)
            #trying to identify the name parts. Define last name as last word
        for name in names:
            if name in dDict.keys():
                dDict[name][0].append(idno)
            else:
                npart=''
                if name in nameparts.keys(): npart=nameparts[name]
                dDict[name] = ([idno,], npart)
    if verbose:
        print 'read %s: from %r lines identified %r items.' % (filename, len(lines), len(dDict))
    return dDict
#done
