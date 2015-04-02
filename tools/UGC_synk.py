#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Mechanism for identifying UGC-objects in lists and adding these to the database
Known problems:
* This is sensitive to the structure of the page.
  e.g. one parameter per row table finished on a separate row etc.
  Problem with using the available common.findUnit is that this
  makes it hard to identify where on the page to add the id.
  Alternative would be to parse each object using common.findUnit
  and re-output it. This has the benifit of structuring unstructured pages
  but risks messing up pages with simple typos.
'''


def run(checkList, pageInfos, wpApi, dbWriteSQL):
    changed = 0
    log = ''
    checkPages = wpApi.getPage(checkList)
    for pagename, contents in checkPages.iteritems():
        changes = UGConPage(pageInfos[pagename]['wikidata'], contents, dbWriteSQL)
        if changes:
            changed += changes[0]
            wpApi.editText(pagename, changes[1], u'Lägger till UGC-id', minor=True, bot=True, userassert='bot')
            log = u'%sUGC objects added to %s\n' % (log, pagename)
    return (log, changed)


def UGConPage(wikidata, contents, dbWriteSQL):
    changed = 0  # number of new UGC objects which were identified
    inTemplate = False  # whether we are currently looking in the right template
    lines = contents.split('\n')
    output = ''

    # loop through page
    for l in lines:
        if inTemplate:
            if l.strip().startswith(u'|}'):
                inTemplate = False
            elif (l.replace(" ", "") == u'|id='):
                changed += 1
                newId = getNewId(wikidata, dbWriteSQL)
                l = u'%s %s' % (l.rstrip(), newId)
        else:
            if l.strip().startswith(u'{{Offentligkonstlista-huvud'):
                inTemplate = True
        output = u'%s\n%s' % (output, l)

    if changed > 0:
        return (changed, output.strip())
    else:
        return None


def getNewId(wikidata, odokWriter):
    # This should ideally be worked into odok.py and be made SQL safe
    queries = []
    queries.append(u'INSERT INTO ugc_table (list) VALUES ("%s"); ' % wikidata)
    queries.append(u'SET @last_UGC_id = CONCAT("UGC/", LAST_INSERT_ID()); ')
    queries.append(u'INSERT INTO main_table (id, muni, county, source, descr, year_cmt, cmt, inside) VALUES (@last_UGC_id,"0","00","UGC", "", "", "", 0); ')
    queries.append(u'SELECT @last_UGC_id;')

    result = odokWriter.multiQuery(queries)
    return result[3][0][0]
