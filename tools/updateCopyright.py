#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tool for updating the copyright status of an object based on the
birth/death year of the artist(s)
ToDO:
    tag free objects with multiple artists
    update unfree object once it becomes free (relies on multi-artistfix)
'''
import odok as odokConnect
import common
config = common.loadJsonConfig()

# Number of years since birth before considering the work to be free (if year of death is unknown)
YEARS_AFTER_BIRTH = 150
# Number of years since death before considering the work to be free
YEARS_AFTER_DEATH = 70


def tagUnfree(dbWriteSQL, testing):
    '''
    identifies unfree objects based on the birth and/or death year of
    the artist and also tags any object with multiple artists
    '''
    if testing:
        query = u"""##would change free=%s\nSELECT `id`, `free`, `title`, `artist` FROM `main_table` """
    else:
        query = u"""UPDATE `main_table` SET free=%s """
    query += u"""WHERE `free` = '' AND `id` IN
    (SELECT `object` FROM `artist_links` WHERE `artist` IN
        (SELECT `id` FROM `artist_table` WHERE
            (
                `death_year` IS NULL
                AND (
                    `birth_year` IS NOT NULL
                    AND
                    `birth_year` + %r > YEAR(CURRENT_TIMESTAMP)
                    )
            )
            OR
            (
                `death_year` IS NOT NULL
                AND
                `death_year` + %r > YEAR(CURRENT_TIMESTAMP)
            )
        )
    );"""
    affected_count, results = dbWriteSQL.query(query, (u'unfree', YEARS_AFTER_DEATH, YEARS_AFTER_DEATH), expectReply=True)
    # do something with the reply
    print u'-----------\n unfree (%d)\nid | free | title | artist' % affected_count
    for row in results:
        print ' | '.join(row)


def tagFree(dbWriteSQL, testing):
    '''
    identifies free objects based on the birth and/or death year of the artist
    skips any object with multiple artists
    '''

    if testing:
        query = u"""##would set free=%s\nSELECT `id`, `free`, `title`, `artist` FROM `main_table` """
    else:
        query = u"""UPDATE `main_table` SET free=%s """
    query += u"""WHERE `free` = '' AND `id` IN
    (SELECT a.`object` FROM `artist_links` a
        JOIN (
            SELECT `object`, COUNT(*) c FROM `artist_links` GROUP BY `object` HAVING c = 1
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
                `death_year` + %r < YEAR(CURRENT_TIMESTAMP)
            )
        )
    );"""
    affected_count, results = dbWriteSQL.query(query, (u'pd', YEARS_AFTER_BIRTH, YEARS_AFTER_DEATH), expectReply=True)
    # do something with the reply
    print u'-----------\n free (%d)\nid | free | title | artist' % affected_count
    for row in results:
        print ' | '.join(row)


def tagOldUnknown(dbWriteSQL, testing):
    '''
    identifies unfree/free objects based on author being unknown and (construction) year being known and :
    * unfree:  year + YEARS_AFTER_DEATH > NOW
    * free:    year + YEARS_AFTER_BIRTH < NOW
    '''
    # Unfree if year + YEARS_AFTER_DEATH > NOW
    if testing:
        query = u"""##would set free=%s\nSELECT `id`, `free`, `title`, `artist` FROM `main_table` """
    else:
        query = u"""UPDATE `main_table` SET free=%s """
    query += u"""WHERE
    `free` = '' AND
    `artist` = '' AND NOT
    `year` = 0 AND
    `year` + %r > YEAR(CURRENT_TIMESTAMP);"""
    affected_count, results = dbWriteSQL.query(query, (u'unfree', YEARS_AFTER_DEATH), expectReply=True)
    # do something with the reply
    print u'-----------\n unfree no artist (%d)\nid | free | title | artist' % affected_count
    for row in results:
        print ' | '.join(row)

    # Free if year + YEARS_AFTER_BIRTH < NOW
    if testing:
        query = u"""##would set free=%s\nSELECT `id`, `free`, `title`, `artist` FROM `main_table` """
    else:
        query = u"""UPDATE `main_table` SET free=%s """
    query += u"""WHERE
    `free` = '' AND
    `artist` = '' AND NOT
    `year` = 0 AND
    `year` + %r < YEAR(CURRENT_TIMESTAMP);"""
    affected_count, results = dbWriteSQL.query(query, (u'pd', YEARS_AFTER_BIRTH), expectReply=True)
    # do something with the reply
    print u'-----------\n free no artist (%d)\nid | free | title | artist' % affected_count
    for row in results:
        print ' | '.join(row)


def showMultipleArtists(dbWriteSQL, testing):
    '''
    identifies free objects with multiple artists missing a copyright status
    '''
    query = u"""SELECT `id`, `free`, `title`, `artist` FROM `main_table` WHERE `free` = '' AND `id` IN
    (SELECT a.`object` FROM `artist_links` a
        JOIN (
            SELECT `object`, COUNT(*) c FROM `artist_links` GROUP BY `object` HAVING c > 1
        ) b ON a.`object`=b.`object`
    );"""
    affected_count, results = dbWriteSQL.query(query, None, expectReply=True)
    # do something with the reply
    print u'-----------\n with multiple artists and no status (%d)\nid | free | title | artist' % affected_count
    for row in results:
        print ' | '.join(row)


def run(testing=False):
    dbWriteSQL = odokConnect.OdokWriter.setUp(host=config['db_server'],
                                              db=config['db'],
                                              user=config['db_edit'],
                                              passwd=config['db_edit_password'],
                                              testing=testing)
    tagUnfree(dbWriteSQL, testing=testing)
    tagFree(dbWriteSQL, testing=testing)
    tagOldUnknown(dbWriteSQL, testing=testing)
    showMultipleArtists(dbWriteSQL, testing=testing)
    dbWriteSQL.closeConnections()
    print 'Done, woho!'

if __name__ == "__main__":
    run()
