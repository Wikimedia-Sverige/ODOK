#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Simple maintanance script which can be run from a cron tab.
1. Synks Wikipedia lists
2. Creates a new geojson file
3. Overwrites the old geojson file
'''
import os
import synking
import updateFeatures

# run synk for two days
synking.run(days=2)

# make new geojson
f = u'AllFeatures.geo.json'
updateFeatures.allGeoJson(filename=f)

# overwrite old geojson once new is ready
target = u'live_site'
os.rename(f, os.path.join(target, f))
