#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Identifies and lists contributors to list articles and extracts some
basic information about these.

The latter is done in order to evaluate which user groups have been reached
'''

import codecs
import json
import common
import WikiApi as wikiApi


def run(start='2015-01-01', end=None):
    config = common.loadJsonConfig()
    # connect to api
    wpApi = wikiApi.WikiApi.setUpApi(user=config['w_username'],
                                     password=config['w_password'],
                                     site=config['wp_site'])
    comApi = wikiApi.CommonsApi.setUpApi(user=config['w_username'],
                                         password=config['w_password'],
                                         site=u'https://commons.wikimedia.org')

    # find changed pages
    pageList = wpApi.getEmbeddedin(u'Mall:Offentligkonstlista', 0)

    contribs, ministats, users = handleContributions(wpApi,
                                                     pageList,
                                                     start=start,
                                                     end=end)

    images, image_users = handleImages(wpApi, comApi, pageList,
                                       start=start, end=end)

    # combine users
    users = list(set(users+image_users))
    userInfo = wpApi.getUserData(users)

    # add some more ministats
    ministats['images'] = len(images)
    ministats['image_users'] = len(list(set(image_users)))
    ministats['list_users'] = ministats['users']
    ministats['users'] = len(users)

    f = codecs.open('users.json', 'w', 'utf8')
    f.write(json.dumps(userInfo, indent=4, ensure_ascii=False))
    f.close()

    f = codecs.open('contribs.json', 'w', 'utf8')
    f.write(json.dumps(contribs, indent=4, ensure_ascii=False))
    f.close()
    print json.dumps(ministats, indent=4, ensure_ascii=False)


def handleImages(wpApi, comApi, pageList, start=None, end=None):
    """
    Given a pagelist get all images displayed in them which were uploaded
    in the timespan
    """
    # quick and dirty date conversion
    validateInput(start, 'start')
    start = dateHack(start, ifNone=0)
    validateInput(end, 'end')
    end = dateHack(end, ifNone=float('inf'))

    # find new images
    images = wpApi.getImages(pageList)

    # identify duplicates and remove any image appearing more than once
    dupes = []
    tmp = []
    for i in images:
        if i in tmp:
            dupes.append(i)
        else:
            tmp.append(i)
    images = list(set(images))
    dupes = list(set(dupes))
    for i in dupes:
        images.remove(i)

    # request timestamps and compare
    imageInfo = comApi.getImageInfo(images)
    valid = []
    users = []
    for k, v in imageInfo.iteritems():
        timestamp = dateHack(v['timestamp'])
        if start < timestamp and end > timestamp:
            valid.append(k)
            users.append(v['user'])

    users = list(set(users))
    return valid, users


def dateHack(date, ifNone=None):
    """
    Quick hack to convert iso-dates to something comparible
    """
    if date is None:
        return ifNone
    else:
        return int(date[:len('YYYY-MM-DD')].replace('-', ''))


def validateInput(date, cmt):
    # validate input
    if date is not None:
        if not common.is_iso_date(date):
            print '%s was not a valid YYYY-MM-DD date' % cmt
            exit
        date = str(date)  # in case of unicode
    return date


def handleContributions(wpApi, pageList, start=None, end=None):
    '''
    Given a pagelist get all off the contribution statistics
    '''
    # validate input
    validateInput(start, 'start')
    validateInput(end, 'end')

    # get all stats
    dDict = {}
    for p in pageList:
        dDict[p] = wpApi.getContributions(p, start=start, end=end)

    # ministats
    ministats = {}
    ministats['pages'] = len(dDict.keys())
    anons_all = []
    users_all = []
    ministats['users_contribs'] = 0
    ministats['size_abs'] = 0
    ministats['size_rel'] = 0
    for page, stats in dDict.iteritems():
        if stats is None:
            continue
        anons_all += stats['users']['_anon']
        tmp_anon = stats['users']['_anon'][:]  # clone
        del stats['users']['_anon']
        users_all += stats['users'].keys()
        ministats['users_contribs'] += sum(stats['users'].values())
        ministats['size_abs'] += stats['size']['absolute']
        ministats['size_rel'] += stats['size']['relative']
        stats['users']['_anon'] = tmp_anon
    anons_all = list(set(anons_all))
    users_all = list(set(users_all))
    ministats['users'] = len(users_all)
    ministats['anons'] = len(anons_all)

    return dDict, ministats, users_all


if __name__ == "__main__":
    import sys
    usage = '''Usage: python contributors.py start end
\tstart (optional): YYYY-MM-DD start date (default 2015-01-01)
\tend (optional): YYYY-MM-DD end date (default None)'''
    argv = sys.argv[1:]
    if len(argv) == 0:
        run()
    elif len(argv) == 1:
        run(start=argv[0])
    elif len(argv) == 2:
        run(start=argv[0], end=argv[1])
    else:
        print usage
# EoF
