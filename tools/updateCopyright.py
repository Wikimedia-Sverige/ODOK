#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tool for updating the copyright status of an object based on the birth/death year of the artist(s)
ToDO:
    tag free objects with multiple artists
    update unfree object once it becomes free (relies on multi-artistfix)
'''
import dconfig as dconfig
import wikipedia
import MySQLdb
import codecs

YEARS_AFTER_BIRTH = 150 #Number of years since birth before considering the work to be free (if year of death is unknown)

def connectDatabase():
    '''
    Connect to the mysql database, if it fails, go down in flames
    '''
    conn = MySQLdb.connect(host=dconfig.db_server, db=dconfig.db, user = dconfig.db_username, passwd = dconfig.db_password, use_unicode=True, charset='utf8')
    cursor = conn.cursor()
    return (conn, cursor)

def tagUnfree(conn, cursor, testing=False):
    '''
    identifies unfree objects based on the birth and/or death year of the artist
    also tags any object with multiple artists
    '''
    if testing: query=u"""##would set free=%s\nSELECT id, free, title, artist FROM `main_table` """
    else: query = u"""UPDATE `main_table` SET free=%s """
    query=query+u"""WHERE `free` = '' AND `id` IN
    (SELECT `object` FROM `artist_links` WHERE `artist` IN
        (SELECT `id` FROM `artist_table` WHERE
            (
                `death_year` IS NULL
                AND (
                    `birth_year` IS NOT NULL
                    AND
                    `birth_year` + 70 > YEAR(CURRENT_TIMESTAMP)
                    )
            )
            OR
            (
                `death_year` IS NOT NULL
                AND
                `birth_year` + 70 > YEAR(CURRENT_TIMESTAMP)
            )
        )
    );"""
    affected_count = cursor.execute(query, (u'unfree',))
    #do something with the reply
    print u'-----------\n unfree (%d)\nid | free | title | artist' %affected_count
    for row in cursor:
        print ' | '.join(row)

def tagFree(conn, cursor, testing=False):
    '''
    identifies free objects based on the birth and/or death year of the artist
    skips any object with multiple artists
    '''
    #YEARS_AFTER_BIRTH = 150 #Number of years since birth to waith befor considering the work to be free (if year of death is unknown)
    
    if testing: query=u"""##would set free=%s\nSELECT id, free, title, artist FROM `main_table` """
    else: query = u"""UPDATE `main_table` SET free=%s """
    query=query+u"""WHERE `free` = '' AND `id` IN
    (SELECT a.`object` FROM `artist_links` a
        JOIN (
            SELECT `object`, COUNT(*) c FROM `artist_links` GROUP BY `object` HAVING c > 1
        ) b ON a.`object`=b.`object` WHERE a.`artist` IN
        (SELECT `id` FROM `artist_table` WHERE
            (`death_year` IS NULL
            AND (
                `birth_year` IS NOT NULL
                AND
                `birth_year` + %r < YEAR(CURRENT_TIMESTAMP)
                )
            )
            OR
            (
                `death_year` IS NOT NULL
                AND
                `birth_year` + 70 < YEAR(CURRENT_TIMESTAMP)
            )
        )
    );"""
    affected_count = cursor.execute(query, (u'pd', YEARS_AFTER_BIRTH))
    #do something with the reply
    print u'-----------\n free (%d)\nid | free | title | artist' %affected_count
    for row in cursor:
        print ' | '.join(row)

def showMultipleArtists(conn, cursor, testing=False):
    '''
    identifies free objects with multiple artists missing a copyright statys
    '''
    query = u"""SELECT id, free, title, artist FROM `main_table` WHERE `free` = '' AND `id` IN
    (SELECT a.`object` FROM `artist_links` a
        JOIN (
            SELECT `object`, COUNT(*) c FROM `artist_links` GROUP BY `object` HAVING c > 1
        ) b ON a.`object`=b.`object`
    );"""
    affected_count = cursor.execute(query)
    #do something with the reply
    print u'-----------\n with multiple artists and no status (%d)\nid | free | title | artist' %affected_count
    for row in cursor:
        print ' | '.join(row)

def testing(testing=True):
    (conn, cursor) = connectDatabase()
    tagUnfree(conn, cursor, testing=testing)
    tagFree(conn, cursor, testing=testing)
    showMultipleArtists(conn, cursor, testing=testing)
    conn.commit() 
    conn.close()
