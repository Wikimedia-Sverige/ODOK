DROP TRIGGER IF EXISTS `main_table`.`audit_trigger`;
DROP TRIGGER IF EXISTS `main_table`.`created_trigger`;
DROP TABLE IF EXISTS `artist_links`;
DROP TABLE IF EXISTS `audit_table`;
DROP TABLE IF EXISTS `main_table`;
DROP TABLE IF EXISTS `muni_table`;
DROP TABLE IF EXISTS `county_table`;
DROP TABLE IF EXISTS `source_table`;
DROP TABLE IF EXISTS `artist_table`;

CREATE TABLE  `muni_table` (
  `id`          smallint(4)     NOT NULL,                   #Kommunkod
  `name`        varchar(255)    NOT NULL,                   #Kommunnamn
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        #article name on wikidata
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`name`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;
INSERT INTO muni_table (id, name) VALUES ("0000", "unknown");
LOAD DATA INFILE "/tmp/muni.dat" INTO TABLE muni_table CHARACTER SET UTF8 FIELDS TERMINATED BY '|' IGNORE 1 LINES (id, name, @dummy, wiki);

CREATE TABLE  `county_table` (
  `id`          varchar(2)      NOT NULL,                   #Länskod
  `name`        varchar(255)    NOT NULL,                   #Länsnamn
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        #article name on wikidata
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`name`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;
INSERT INTO county_table (id, name) VALUES ("00", "unknown");
LOAD DATA INFILE "/tmp/county.dat" INTO TABLE county_table CHARACTER SET UTF8 FIELDS TERMINATED BY '|' IGNORE 1 LINES (id, name, @dummy, wiki);

CREATE TABLE  `source_table` (
  `id`          varchar(25)     NOT NULL,                   # Unikt id för källan
  `name`        varchar(255)    NOT NULL,                   # Källans hela namn
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        # Article name on wikidata
  `real_id`     bit(1)          NOT NULL DEFAULT 1,         # Försåg de oss med egna id? t/f = 1/0
  `url`         varchar(255)    NOT NULL DEFAULT '',        # Källans webbsida
  `changed`     timestamp       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, # Senast ändrad
  `cmt`         text            NOT NULL DEFAULT '',        # Kommentar om datakällan (t.ex. bara utomhusföremål, bara ägda av kommunene etc.)
  #`updates`    bit(1)          NOT NULL DEFAULT 0,         # Vill de ha uppdaterad data? t/f = 1/0
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`name`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;

CREATE TABLE  `artist_table` (
  `id`          int             NOT NULL AUTO_INCREMENT,    # Unikt id för artisten
  `first_name`  varchar(255)    NOT NULL,                   # Förnamn (eller hela namnet?)
  `last_name`   varchar(255)    NOT NULL DEFAULT '',        # Efternamn
  `wiki`        varchar(255)    NOT NULL DEFAULT '',        # Article name on wikidata
  `changed`     timestamp       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, # Senast ändrad
  `birth_date`  date            DEFAULT NULL,               # Birth date (full iso date)
  `death_date`  date            DEFAULT NULL,               # Death date (full iso date)
  `birth_year`  year            DEFAULT NULL,               # Birth year (automatically filled in if birth_date is entered)
  `death_year`  year            DEFAULT NULL,               # Death year (automatically filled in if death_date is entered)
  `creator`     varchar(255)    NOT NULL DEFAULT '',        # Creator template on commons
  `cmt`         text            NOT NULL DEFAULT '',        # Kommentar om artisten (t.ex. källa för informationen etc.)
  PRIMARY KEY   `id` (`id`),
  INDEX         `name` (`first_name`, `last_name`),
  INDEX         `death` (`death_year`),
  INDEX         `birth` (`birth_year`),
  INDEX         `wiki` (`wiki`)
)ENGINE=INNODB DEFAULT CHARSET=utf8;

#avoid using NULL as default since this makes trigger comparisons bulky
CREATE TABLE  `main_table` (
  `id`          varchar(25)     NOT NULL,                   # Unikt id
  `title`       varchar(255)    NOT NULL DEFAULT '',        # Namn
  `artist`      varchar(255)    NOT NULL DEFAULT '',        # Konstnär
  `descr`       text            NOT NULL DEFAULT '',        # Beskrivning (fritext) (text?)
  `year`        smallint(4)     NOT NULL DEFAULT '0000',    # årtal, 0000 som okänd
  `year_cmt`    text            NOT NULL DEFAULT '',        # Kommentar om år är okänt
  `type`        varchar(255)    NOT NULL DEFAULT '',        # typ av konstverk (table?)
  `material`    varchar(255)    NOT NULL DEFAULT '',        # material konstverket är gjort av (fritext)
  `inside`      bit(1)          NOT NULL,                   # inomhus eller utomhus, för FoP
  `address`     varchar(255)    NOT NULL DEFAULT '',        # adress för konstverk (relevant?)
  `county`      varchar(2)      NOT NULL REFERENCES county_table(id),   # länskod, 00 som okänd
  `muni`        smallint(4)     NOT NULL REFERENCES muni_table(id),     # kommunkod, 0000 som okänd
  `district`    varchar(255)    NOT NULL DEFAULT '',        # stadsdel
  `lat`         double          DEFAULT NULL,               # WGS84 latitude (decimal format)
  `lon`         double          DEFAULT NULL,               # WGS84 longitud (decimal format)
  `image`       varchar(255)    NOT NULL DEFAULT '',        # Bildnamn hos Commons
  `source`      varchar(25)     NOT NULL REFERENCES source_table(id),   # Källa för info (organisation)
  `ugc`         bit(1)          NOT NULL DEFAULT 0,         # Flagga för om det är originalinfo t/f =1/0
  `changed`     timestamp       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, # Senast ändrad
  `created`     timestamp,                                  # När objektet lades in i databasen (får rätt värde genom created_trigger)
  `wiki_article` varchar(255)   NOT NULL DEFAULT '',        # WikiData id för artikel om konstverket
  `commons_cat`  varchar(255)   NOT NULL DEFAULT '',        # Objektspecifik kategori på Commons
  `official_url` varchar(255)   NOT NULL DEFAULT '',        # Officiell sida om objektet (på källans webplats)
  `same_as`     varchar(25)     DEFAULT NULL REFERENCES main_table(id), # Om samma objekt har två id (t.ex. kommit från kommun och län)
  `free`        enum('','pd','cc','unfree') NOT NULL DEFAULT '',        # Om objektet är upphovsrättsligt fritt. '' då okänd.
  #`free_cmt`   text            NOT NULL DEFAULT '',        # Motivation för free status t.ex. artist dödsår ifall inget artist_id
  `owner`       varchar(255)    NOT NULL DEFAULT '',        # Ägare av, eller ansvarig för, objektet
  `cmt`         text            NOT NULL DEFAULT '',        # Kommentarer så som tillfälligt, stod tidigare nån annnan stans etc.
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
  `object`      varchar(25)     NOT NULL REFERENCES main_table(id),     #Objekt_id
  `artist`      int             NOT NULL REFERENCES artist_table(id),   #Konstnärs_id
  PRIMARY KEY   `object-artist` (`object`, `artist`),
  UNIQUE INDEX  `artist-object` (`artist`, `object`),
  #Because mysql does not support inline referenes
  FOREIGN KEY (object)  REFERENCES main_table(id),
  FOREIGN KEY (artist)  REFERENCES artist_table(id)
)ENGINE=INNODB DEFAULT CHARSET=utf8;
