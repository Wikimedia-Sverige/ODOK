# -*- coding: UTF-8  -*-
#
# Methods comonly shared by the tool scripts
#
import codecs
import os
import operator
import urllib, urllib2
from json import loads

class Common:
    @staticmethod
    def openFile(filename):
        '''opens a given file (utf-8) and returns the lines)'''
        fin = codecs.open(filename, 'r', 'utf-8')
        txt = fin.read()
        fin.close()
        lines = txt.split('\n')
        lines.pop()
        return lines
    
    @staticmethod
    def sortedDict(ddict):
        '''turns a dict into a sorted list'''
        sorted_ddict = sorted(ddict.iteritems(), key=operator.itemgetter(1), reverse=True)
        return sorted_ddict
    
    @staticmethod
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def file_to_dict(filename, idcol=0, namecol=1, verbose=False):
        '''reads in a file and passes it to a dict where each row is in turn a dict
           lines starting with # are treated as comments. Semicolons in the namecol are treated as separate names.
           Sqare brakets as the real value (i.e. rest is ignored)'''
        listcols = isinstance(namecol,list)
        if listcols and len(namecol) != 2:
            print u'namecol must be a single integer or two integers'
        lines = Common.openFile(filename)
        dDict = {}
        for l in lines:
            if len(l)==0 or l.startswith(u'#'):
                continue
            col = l.split('|')
            idno = col[idcol]
            nameparts={}
            #names can be constructed by two columns (first name, last name)
            if listcols: #
                namesF = Common.extractName(col[namecol[0]])
                namesL = Common.extractName(col[namecol[1]])
                names=[]
                for i in range(0,len(namesF)):
                    names.append(u'%s %s' % (namesF[i],namesL[i]))
                    nameparts[u'%s %s' % (namesF[i],namesL[i])] = u'%s;%s' %(namesF[i],namesL[i])
            else:
                names = Common.extractName(col[namecol])
                #trying to identify the name parts
                for name in names:
                    nameparts[name] = Common.extractNameParts(name)
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
    
    @staticmethod
    def extractName(entry):
        '''If field includes square brackets then this ignores any part of name field which lies outside
           If field contains semicolons then treats thes as separate objects'''
        if u'[' in entry:
            pos1 = entry.find(u'[')
            pos2 = entry.find(u']')
            entry = entry[pos1+1:pos2]
        return entry.split(u';')
    
    @staticmethod
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
            lName = parts[len(parts)-1].strip()
            fName = name[:-len(lName)].strip()
            return u'%s;%s' %(fName,lName)
        return name
    
    @staticmethod
    def getWikidata(article, verbose=False):
        '''returns the wikidata enitity id of an article'''
        wikiurl = u'https://www.wikidata.org'
        apiurl = '%s/w/api.php' %wikiurl
        urlbase = '%s?action=wbgetentities&format=json&sites=svwiki&props=info&titles=' %apiurl
        url = urlbase+urllib.quote(article.encode('utf-8'))
        req = urllib2.urlopen(url)
        j = loads(req.read())
        req.close()
        if (j['success'] == 1) or (not 'warnings' in j.keys()) or (not len(j['entities'])==1):
            if j['entities'].keys()[0] == u'-1':
                if verbose: print 'no entry'
                return (None, 'no entry')
            else:
                if verbose: print u'Found the wikidata entry at %s' %j['entities'].keys()[0]
                return (j['entities'].keys()[0],'')
        else:
            error = 'success: %s, warnings: %s, entries: %d' %(j['success'], 'warnings' in j.keys(), len(j['entities']))
            if verbose: print error
            return (None, error)
    
    @staticmethod
    def getManyWikidata(articles, dDict, verbose=False):
        '''returns the wikidata enitity ids of a list of articles'''
        if not isinstance(articles,list):
            print '"getManyWikidata" requiresa list of articles. for individual articles use "getWikidata" instead'
            return None
        #do an upper limit check (max 50 titles per request allowed)
        if len(articles) > 50:
            i=0
            while True:
                Common.getManyWikidata(articles[i:i+50], dDict, verbose=verbose)
                i=i+50
                if i+50 > len(articles):
                    Common.getManyWikidata(articles[i:], dDict, verbose=verbose)
                    break
        elif len(articles) > 0:
            wikiurl = u'https://www.wikidata.org'
            apiurl = '%s/w/api.php' %wikiurl
            urlbase = '%s?action=wbgetentities&format=json&sites=svwiki&props=info|sitelinks&titles=' %apiurl
            url = urlbase+urllib.quote('|'.join(articles).encode('utf-8'))
            if verbose: print url
            req = urllib2.urlopen(url)
            j = loads(req.read())
            req.close()
            if (j['success'] == 1) or (not 'warnings' in j.keys()) or (not len(j['entities'])==1):
                for k, v in j['entities'].iteritems():
                    if k.startswith(u'q'):
                        title = v['sitelinks']['svwiki']['title']
                        dDict[title] = k
                        if verbose: print u'%s: Found the wikidata entry at %s' %(title,k)
                    else:
                        title = v['title']
                        dDict[title] = None
                        if verbose: print '%s: no entry' %title
            else:
                error = 'success: %s, warnings: %s, entries: %d' %(j['success'], 'warnings' in j.keys(), len(j['entities']))
                if verbose: print error
                return (None, error)
    
    @staticmethod
    def getManyArticles(wikidata, dDict, verbose=False):
        '''returns the articles of a list of wikidata enitity ids'''
        if not isinstance(wikidata,list):
            print '"getManyArticles" requiresa list of articles. for individual wikidata entities use "getArticles" instead'
            return None
        #do an upper limit check (max 50 titles per request allowed)
        if len(wikidata) > 50:
            i=0
            while True:
                Common.getManyArticles(wikidata[i:i+50], dDict, verbose=verbose)
                i=i+50
                if i+50 > len(wikidata):
                    Common.getManyArticles(wikidata[i:], dDict, verbose=verbose)
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
#done
