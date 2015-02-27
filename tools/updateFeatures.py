#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# Quick script for updating the geoJson file used (at some future point) on the homepage
#
import codecs, ujson, datetime
import odok as odokConnect
import dconfig as config


def allGeoJson(filename="../site/AllFeatures.geo.json", source=None, full=True, debug=False):
    '''
    repetedly queries api for geojson of all features and
    outputs a file with the data
    '''
    out = codecs.open(filename, 'w', 'utf8')
    dbApi = odokConnect.OdokApi.setUpApi(user=config.odok_user, site=config.odok_site)

    features = dbApi.getGeoJson(full=full, source=source, debug=debug)

    print u'processing %d features' % len(features)
    newFeatures = []
    for feature in features:
        if feature['properties']['same_as']:
            continue
        newFeatures.append(feature)


    outJson = {"type": "FeatureCollection",
	       "features": newFeatures,
           "head": {
                "status": "1",
                "hits": len(features),
                "timestamp": datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
    out.write(ujson.dumps(outJson))  # , ensure_ascii=False))
    out.close()
    print '%s was created with %d features' % (filename, len(features))


if __name__ == "__main__":
    allGeoJson()
