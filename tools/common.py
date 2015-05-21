#!/usr/bin/python
# -*- coding: UTF-8  -*-
#
# Methods comonly shared by the tool scripts
#
import codecs
import operator  # only for sortedDict()
import sys  # only for raw_encoded_input()
import locale  # only for raw_encoded_input()
import json  # for loadJsonConfig


def loadJsonConfig(filename='config.json'):
    '''
    Load and return json config file as a dict.
    Looks in local directory first.
    If file isn't there then looks in user directory.
    If file is in neither location then error is raised
    '''
    try:
        f = open(filename, 'r')
        config = json.load(f)
        f.close()
    except IOError, e:
        if e.errno == 2:  # file not found
            import os
            path = os.getenv("HOME")
            f = open('%s/%s' % (path, filename), 'r')
            config = json.load(f)
            f.close()
        else:
            raise
    return config


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
    sorted_ddict = sorted(ddict.iteritems(),
                          key=operator.itemgetter(1),
                          reverse=True)
    return sorted_ddict


def is_number(s):
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def is_int(s):
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


def is_iso_date(s):
    '''
    Checks if a string is a valid YYYY-MM-DD date
    NOTE: Does not validate if length of month is < 31
    '''
    if not isinstance(s, str) or isinstance(s, unicode):
        return False
    if not len(s) == len('YYYY-MM-DD'):
        return False
    if not s[4:5] == '-' and s[7:8] == '-':
        return False
    y, m, d = s[:4], s[5:7], s[8:]
    if not is_int(y):
        return False
    if not (is_int(m) and int(m) in range(1, 12)):
        return False
    if not (is_int(d) and int(d) in range(1, 31)):
        return False
    return True


def raw_encoded_input(txt):
    '''query for input and deal with the encoding, whatever it is'''
    return raw_input(txt).decode(sys.stdin.encoding or
                                 locale.getpreferredencoding(True))


def list_diff(a, b):
    '''subtract list 2 from list 1'''
    b = set(b)
    return [aa for aa in a if aa not in b]


def extractName(entry):
    '''
    If field includes square brackets then this ignores any part of
        name field which lies outside
    If field contains semicolons then treats these as separate objects
    '''
    if u'[' in entry:
        pos1 = entry.find(u'[')
        pos2 = entry.find(u']')
        entry = entry[pos1+1:pos2]
    return entry.split(u';')


def extractNameParts(name):
    '''Tries to separate a name into first and second name.'''
    # Algorithm. If one "," in names then asume lName, fName.
    # Else asume last name is the last word of the name.
    # Plain name returned if all else fails
    if u',' in name:
        parts = name.split(u',')
        if len(parts) == 2:
            return u'%s;%s' % (parts[1].strip(), parts[0].strip())
    if u' ' in name:
        parts = name.split(u' ')
        lName = parts[-1].strip()
        fName = name[:-len(lName)].strip()
        return u'%s;%s' % (fName, lName)
    return name


def findUnit(contents, start, end, brackets=None):
    '''
    Method for isolating an object in a string. Will not work with
    either start or end using the ¤ symbol
    @input:
        * content: the string to look at
        * start: the substring indicateing the start of the object
        * end: the substring indicating the end of the object
            if end is not found then the rest of the string is returned
            if explicitly set to None then it is assumed that start-string
                also marks the end of an object. In this case the end-string
                is returned as part of the remainder
        * brackets: a dict of brackets used which must match within the object
    @output:
        the-object, the-remainder-of-the-string, lead-in-to-object
        OR None,None if an error
        OR '','' if no object is found
    '''
    if start in contents:
        # If end is left blank
        if end is None:
            noEnd = True
            end = start
        else:
            noEnd = False

        uStart = contents.find(start) + len(start)
        uEnd = contents.find(end, uStart)
        if uEnd < 0:  # process till end of string
            uEnd = None
        if brackets:
            for bStart, bEnd in brackets.iteritems():
                dummy = u'¤'*len(bEnd)
                diff = contents[uStart:uEnd].count(bStart) - contents[uStart:uEnd].count(bEnd)
                if diff < 0:
                    print 'Negative bracket missmatch for: %s <--> %s' % (bStart, bEnd)
                    return None, None, None
                # two cases either end is one of these brackets or not
                if end in bEnd:  # end is part of endBracket
                    i = 0
                    while(diff > 0):
                        i += 1
                        uEnd = contents.replace(bEnd, dummy, i).find(end, uStart)
                        if uEnd < 0:
                            print 'Positive (final) bracket missmatch for: %s <--> %s' % (bStart, bEnd)
                            return None, None, None
                        diff = contents[uStart:uEnd].count(bStart) - contents[uStart:uEnd].count(bEnd)
                else:  # end is different from endBracket (e.g. a '|')
                    i = 0
                    while(diff > 0):
                        i += 1
                        uEnd = contents.find(end, uEnd+len(end))
                        if uEnd < 0:
                            diff = contents[uStart:].count(bStart) - contents[uStart:].count(bEnd)
                            if diff > 0:
                                print 'Positive (final) bracket missmatch for: %s <--> %s' % (bStart, bEnd)
                                return None, None, None
                        else:
                            diff = contents[uStart:uEnd].count(bStart) - contents[uStart:uEnd].count(bEnd)

        unit = contents[uStart:uEnd]
        lead_in = contents[:uStart-len(start)]
        if uEnd:  # i.e. if not until end of string
            if noEnd:
                remainder = contents[uEnd:]
            else:
                remainder = contents[uEnd+len(end):]
        else:
            remainder = ''
        return (unit, remainder, lead_in)
    else:
        return '', '', ''


def extractLink(text, kill_tags=False):
    '''
    Given wikitiext this checks for the first wikilink
    Limitations: Only identifies the first wikilink
    kill_tags also strips out (but doesn't keep) and tags
    (i.e. <bla> something </bla>)
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

    if u'[[' not in text:
        return (text.strip(), '')
    interior, dummy, dummy = findUnit(text, u'[[', u']]')
    wikilink = u'[['+interior+u']]'
    pos = text.find(wikilink)
    pre = text[:pos]
    post = text[pos+len(wikilink):]
    center = ''
    link = ''

    # determine which type of link we are dealing with see meta:Help:Links#Wikilinks for details
    if u'|' not in interior:  # [[ab]] -> ('ab', 'ab')
        center = interior
        link = interior.strip()
    else:
        pos = interior.find(u'|')
        link = interior[:pos]
        center = interior[pos+1:]
        if len(link) == 0:  # [[|ab]] -> ('ab', 'ab')
            link = center
        elif len(center) > 0:  # [[a|b]] -> ('b', 'a')
            pass
        else:
            center = link
            if u':' in center:  # [[a:b|]] -> ('b', 'a:b')
                center = center[center.find(u':')+1:]
            if u', ' in center:  # [[a, b|]] -> ('a', 'a, b')
                center = center.split(u', ')[0]
            if u'(' in center:  # [[a (b)|]] -> ('a', 'a (b)')
                pos = center.find(u'(')
                if u')' in center[pos:]:
                    center = center[:pos]
                    if center.endswith(' '):  # the first space separating text and bracket is ignored
                        center = center[:-1]
    return ((pre+center+post).strip(), link.strip())


def extractAllLinks(text, kill_tags=False):
    '''
    Given wikitext this checks for any wikilinks
    @output: (plain_text, list of link)
    '''
    wikilinks = []
    text, link = extractLink(text, kill_tags=kill_tags)
    while link:
        wikilinks.append(link)
        text, link = extractLink(text, kill_tags=kill_tags)
    return text, wikilinks


def latLonFromCoord(coord):
    '''
    returns lat, lon as decimals based on string using the Coord-template
    Does not deal with {{coord|12.123|12.123|...}}
    @output (lat,lon) as float
    '''
    prefixes = (u'{{coord|', u'{{coord |', u'{{coor|', u'{{coor |', u'{{location|', u'{{location |')
    if not coord.lower().startswith(prefixes):
        print 'incorrectly formated coordinate (prefix): %s' % coord
        return None
    p = coord.split('|')

    if is_number(p[1]):  #
        try:
            if is_number(p[2].rstrip('}')):  #
                if len(p) == 3:  # {{coord|12.123|12.123}} implicitly N, E
                    lat = float(p[1].strip())
                    lon = float(p[2].strip().rstrip('}'))
                    lat_sign = u'N'
                    lon_sign = u'E'
                elif is_number(p[3]):  # {{coord|12|12|12.123|N|12|12|12.123|E|...}}
                    lat_d, lat_m, lat_s, lat_sign = float(p[1].strip()), float(p[2].strip()), float(p[3].strip()), p[4].strip().rstrip('}')
                    lon_d, lon_m, lon_s, lon_sign = float(p[5].strip()), float(p[6].strip()), float(p[7].strip()), p[8].strip().rstrip('}')
                    lat = lat_d + lat_m/60 + lat_s/3600
                    lon = lon_d + lon_m/60 + lon_s/3600
                else:  # {{coord|12|12.123|N|12|12.123|E|...}}
                    lat_d, lat_m, lat_sign = float(p[1].strip()), float(p[2].strip()), p[3].strip().rstrip('}')
                    lon_d, lon_m, lon_sign = float(p[4].strip()), float(p[5].strip()), p[6].strip().rstrip('}')
                    lat = lat_d + lat_m/60
                    lon = lon_d + lon_m/60
            else:  # {{coord|12.123|N|12.123|E|...}}
                lat, lat_sign = float(p[1].strip()), p[2].strip().rstrip('}')
                lon, lon_sign = float(p[3].strip()), p[4].strip().rstrip('}')
            if lat_sign == u'N':
                lat_sign = 1
            elif lat_sign == u'S':
                lat_sign = -1
            else:
                print 'incorrectly formated coordinate (lat_sign): %s, %s' % (lat_sign, coord)
                return None
            if lon_sign == u'E':
                lon_sign = 1
            elif lon_sign == u'W':
                lon_sign = -1
            else:
                print 'incorrectly formated coordinate (lon_sign): %s, %s' % (lon_sign, coord)
                return None
            lat = lat_sign*lat
            lon = lon_sign*lon
            return (lat, lon)
        except IndexError:
            print 'incorrectly formated coordinate (?): %s' % coord
    else:
        print 'incorrectly formated coordinate (content): %s' % coord
