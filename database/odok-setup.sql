DROP TRIGGER IF EXISTS `main_table`.`audit_trigger`;
DROP TRIGGER IF EXISTS `main_table`.`created_trigger`;
DROP TABLE IF EXISTS `artist_links`;
DROP TABLE IF EXISTS `aka_table`;
DROP TABLE IF EXISTS `audit_table`;
DROP TABLE IF EXISTS `main_table`;
DROP TABLE IF EXISTS `muni_table`;
DROP TABLE IF EXISTS `county_table`;
DROP TABLE IF EXISTS `source_table`;
DROP TABLE IF EXISTS `artist_table`;

CREATE TABLE  `muni_table` (
  `id`          smallint(4)     NOT NULL,                   #Municipal code
  `name`        varchar(255)    NOT NULL,                   #Name of municipality
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        #article name on wikidata
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`name`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;
INSERT INTO muni_table (id, name) VALUES ("0000", "unknown");
LOAD DATA INFILE "/tmp/muni.dat" INTO TABLE muni_table CHARACTER SET UTF8 FIELDS TERMINATED BY '|' IGNORE 1 LINES (id, name, @dummy, wiki);

CREATE TABLE  `county_table` (
  `id`          varchar(2)      NOT NULL,                   #County code
  `name`        varchar(255)    NOT NULL,                   #Name of county
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        #article name on wikidata
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`name`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;
INSERT INTO county_table (id, name) VALUES ("00", "unknown");
LOAD DATA INFILE "/tmp/county.dat" INTO TABLE county_table CHARACTER SET UTF8 FIELDS TERMINATED BY '|' IGNORE 1 LINES (id, name, @dummy, wiki);

CREATE TABLE  `source_table` (
  `id`          varchar(25)     NOT NULL,                   # Unique id for the source
  `name`        varchar(255)    NOT NULL,                   # Full name of the source
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        # Article name on wikidata
  `real_id`     bit(1)          NOT NULL DEFAULT 1,         # Did they provide their own ids? t/f = 1/0
  `url`         varchar(255)    NOT NULL DEFAULT '',        # Source webpage
  `changed`     timestamp       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, # Last changed
  `cmt`         text            NOT NULL DEFAULT '',        # Comment for source (e.g. only outdoor objects, only objects owned by the municipality etc.)
  #`updates`    bit(1)          NOT NULL DEFAULT 0,         # Did they request updated data? t/f = 1/0
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`name`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;

CREATE TABLE  `aka_table` (
  `id`          int             NOT NULL AUTO_INCREMENT,    # Unique id for the aka
  `title`       varchar(255)    NOT NULL,                   # The alternative title
  `main_id`     varchar(25)     NOT NULL REFERENCES source_table(id),   # id for the object
  PRIMARY KEY   `id` (`id`),
  INDEX         `title` (`title`),
  INDEX         `main_id` (`main_id`),
  #Because mysql does not support inline referenes
  FOREIGN KEY (main_id)      REFERENCES main_table(id)
)ENGINE=INNODB DEFAULT CHARSET=utf8;

CREATE TABLE  `artist_table` (
  `id`          int             NOT NULL AUTO_INCREMENT,    # Unique id for the artist
  `first_name`  varchar(255)    NOT NULL,                   # First name (or whole name if no last name)
  `last_name`   varchar(255)    NOT NULL DEFAULT '',        # Last name
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        # Article name on wikidata
  `changed`     timestamp       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, # Last changed
  `birth_date`  date            DEFAULT NULL,               # Birth date (full iso date)
  `death_date`  date            DEFAULT NULL,               # Death date (full iso date)
  `birth_year`  year            DEFAULT NULL,               # Birth year (automatically filled in if birth_date is entered)
  `death_year`  year            DEFAULT NULL,               # Death year (automatically filled in if death_date is entered)
  `creator`     varchar(255)    NOT NULL DEFAULT '',        # Creator template on commons
  `cmt`         text            NOT NULL DEFAULT '',        # Comment for artisten (e.g. source of information etc.)
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`first_name`, `last_name`),
  INDEX         `death` (`death_year`),
  INDEX         `birth` (`birth_year`),
  INDEX         `wiki` (`wiki`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;

#avoid using NULL as default since this makes trigger comparisons bulky
CREATE TABLE  `main_table` (
  `id`          varchar(25)     NOT NULL,                   # Unique id
  `title`       varchar(255)    NOT NULL DEFAULT '',        # Namn of artwork
  `artist`      varchar(255)    NOT NULL DEFAULT '',        # Artist
  `descr`       text            NOT NULL DEFAULT '',        # Description (free text)
  `year`        smallint(4)     NOT NULL DEFAULT '0000',    # year, 0000 if unknown
  `year_cmt`    text            NOT NULL DEFAULT '',        # Comment about year (e.g. why unknown or to specify completionyear or erectionyear etc.)
  `type`        varchar(255)    NOT NULL DEFAULT '',        # type of artwork (table?)
  `material`    varchar(255)    NOT NULL DEFAULT '',        # material the artwork is made of (freetext) (Could make it a separate table)
  `inside`      bit(1)          NOT NULL,                   # indoors or outdoors, for FoP
  `address`     varchar(255)    NOT NULL DEFAULT '',        # address/placement of object
  `county`      varchar(2)      NOT NULL REFERENCES county_table(id),   # coutny code, 00 if unknown
  `muni`        smallint(4)     NOT NULL REFERENCES muni_table(id),     # municipal code, 0000 if unknown
  `district`    varchar(255)    NOT NULL DEFAULT '',        # district of city or town in a rural municipality
  `lat`         double          DEFAULT NULL,               # WGS84 latitude (decimal format)
  `lon`         double          DEFAULT NULL,               # WGS84 longitud (decimal format)
  `image`       varchar(255)    NOT NULL DEFAULT '',        # Image name on Wikimedia Commons
  `source`      varchar(25)     NOT NULL REFERENCES source_table(id),   # Source of information (organisation)
  `ugc`         bit(1)          NOT NULL DEFAULT 0,         # Flag indicating whether information has been modified t/f =1/0
  `changed`     timestamp       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, # last changed
  `created`     timestamp,                                  # timstamp for entry into database (gets its value through the created_trigger)
  `wiki_article` varchar(255)   NOT NULL DEFAULT '',        # Wikidata id for the article about the artwork
  `commons_cat`  varchar(255)   NOT NULL DEFAULT '',        # Object specific category on Wikimedia Commons
  `official_url` varchar(255)   NOT NULL DEFAULT '',        # Official page about the object (on source web page)
  `same_as`     varchar(25)     DEFAULT NULL REFERENCES main_table(id), # If this is a duplicate of an exisitnig object (e.g. object provided by two sources)
  `free`        enum('','pd','cc','unfree') NOT NULL DEFAULT '',        # If the object is free (copyrightwise). '' if unknown
  #`free_cmt`   text            NOT NULL DEFAULT '',        # Motivation for free status (e.g. artist deathyear if no linked artist)
  `owner`       varchar(255)    NOT NULL DEFAULT '',        # Owner of, or carer for, the object
  `cmt`         text            NOT NULL DEFAULT '',        # Comments such as temporary placements, previously placed somewhere else, damaged etc.
  PRIMARY KEY   `id` (`id`),
  INDEX         `title` (`title`),
  INDEX         `county` (`county`),
  INDEX         `muni` (`muni`),
  INDEX         `district` (`district`),
  INDEX         `artist` (`artist`),
  INDEX         `year` (`year`),
  INDEX         `type` (`type`),
  INDEX         `coord` (`lat`, `lon`),
  INDEX         `free` (`free`),
  INDEX         `owner`(`owner`),
  #Because mysql does not support inline referenes
  FOREIGN KEY (county)  REFERENCES county_table(id),
  FOREIGN KEY (muni)    REFERENCES muni_table(id),
  FOREIGN KEY (source)  REFERENCES source_table(id),
  FOREIGN KEY (same_as) REFERENCES main_table(id)
)ENGINE=INNODB DEFAULT CHARSET=utf8;

#only includes parameters that are straight from the original source
CREATE TABLE  `audit_table` (
  `id`          varchar(25)     NOT NULL REFERENCES main_table(id),
  `title`       varchar(255),
  `artist`      varchar(255),
  `descr`       text,
  `year`        smallint(4),
  `year_cmt`    text,
  `type`        varchar(255),
  `material`    varchar(255),
  `inside`      bit(1),
  `address`     varchar(255),
  `county`      varchar(2)      REFERENCES county_table(id),
  `muni`        smallint(4)     REFERENCES muni_table(id),
  `district`    varchar(255),
  `lat`         double,                                     # can be null
  `lon`         double,                                     # can be null
  `source`      varchar(25)     REFERENCES source_table(id),
  `official_url` varchar(255),
  `owner`       varchar(255),
  `cmt`         text,
  `created`     timestamp       NOT NULL DEFAULT CURRENT_TIMESTAMP, # timstamp for when change to original was introuduced
  PRIMARY KEY   `id` (`id`),
  INDEX         `title` (`title`),
  INDEX         `county` (`county`),
  INDEX         `muni` (`muni`),
  INDEX         `district` (`district`),
  INDEX         `artist` (`artist`),
  INDEX         `year` (`year`),
  INDEX         `type` (`type`),
  INDEX         `coord` (`lat`, `lon`),
  INDEX         `owner`(`owner`),
  INDEX         `source` (`source`),
  FOREIGN KEY (id)      REFERENCES main_table(id),
  FOREIGN KEY (county)  REFERENCES county_table(id),
  FOREIGN KEY (muni)    REFERENCES muni_table(id),
  FOREIGN KEY (source)  REFERENCES source_table(id)
)ENGINE=INNODB DEFAULT CHARSET=utf8;

CREATE TABLE  `artist_links` (
  `object`      varchar(25)     NOT NULL REFERENCES main_table(id),     #Object id
  `artist`      int             NOT NULL REFERENCES artist_table(id),   #Artist id
  PRIMARY KEY   `object-artist` (`object`, `artist`),
  UNIQUE INDEX  `artist-object` (`artist`, `object`),
  #Because mysql does not support inline referenes
  FOREIGN KEY (object)  REFERENCES main_table(id),
  FOREIGN KEY (artist)  REFERENCES artist_table(id)
)ENGINE=INNODB DEFAULT CHARSET=utf8;
