#Timestamp updating needs to be fixed
DROP TRIGGER IF EXISTS `audit_trigger`;
DROP TRIGGER IF EXISTS `created_trigger`;

#A workaround for MySQL inability to have two timestamps defaulting to CURRENT_TIMESTAMP
DELIMITER |
CREATE TRIGGER `created_trigger` BEFORE INSERT ON main_table
    FOR EACH ROW BEGIN
    SET NEW.created = NULL;
END;
|
DELIMITER ;

#The following two triggers should be merged by calling the same procedure
#If date is given then also fills in year
DELIMITER |
CREATE TRIGGER `date_trigger_in` BEFORE INSERT ON artist_table
    FOR EACH ROW BEGIN
    IF NOT NEW.birth_date IS NULL THEN
        IF NEW.birth_year IS NULL THEN
            SET NEW.birth_year = EXTRACT(YEAR FROM NEW.birth_date);
        END IF;
    END IF;
    IF NOT NEW.death_date IS NULL THEN
        IF NEW.death_year IS NULL THEN
            SET NEW.death_year = EXTRACT(YEAR FROM NEW.death_date);
        END IF;
    END IF;
END;
|
DELIMITER ;

#If date is given then also fills in year
DELIMITER |
CREATE TRIGGER `date_trigger_up` BEFORE Update ON artist_table
    FOR EACH ROW BEGIN
    IF NOT NEW.birth_date IS NULL THEN
        IF NEW.birth_year IS NULL THEN
            SET NEW.birth_year = EXTRACT(YEAR FROM NEW.birth_date);
        END IF;
    END IF;
    IF NOT NEW.death_date IS NULL THEN
        IF NEW.death_year IS NULL THEN
            SET NEW.death_year = EXTRACT(YEAR FROM NEW.death_date);
        END IF;
    END IF;
END;
|
DELIMITER ;


DELIMITER |
CREATE TRIGGER `audit_trigger` BEFORE UPDATE ON main_table
    FOR EACH ROW BEGIN
    DECLARE tmp_date TIMESTAMP DEFAULT NULL;
    IF (OLD.ugc=0) AND (
        #list of parmeters whose changes trigger an audit (gets complicated if content can be null)
        OLD.title != NEW.title OR
        OLD.artist != NEW.artist OR
        OLD.descr != NEW.descr OR
        OLD.year != NEW.year OR
        OLD.year_cmt != NEW.year_cmt OR
        OLD.type != NEW.type OR
        OLD.material != NEW.material OR
        OLD.inside != NEW.inside OR
        OLD.address != NEW.address OR
        OLD.county != NEW.county OR
        OLD.muni != NEW.muni OR
        OLD.district != NEW.district OR
        ((OLD.lat IS NULL AND NEW.lat IS NOT NULL) OR (OLD.lat IS NOT NULL AND NEW.lat IS NULL) OR (OLD.lat IS NOT NULL AND NEW.lat IS NOT NULL AND OLD.lat != NEW.lat)) OR
        ((OLD.lon IS NULL AND NEW.lon IS NOT NULL) OR (OLD.lon IS NOT NULL AND NEW.lon IS NULL) OR (OLD.lon IS NOT NULL AND NEW.lon IS NOT NULL AND OLD.lon != NEW.lon)) OR
        OLD.source != NEW.source OR
        OLD.owner != NEW.owner OR
        OLD.official_url != NEW.official_url OR
        OLD.cmt != NEW.cmt
    ) THEN
        INSERT INTO audit_table SET id = OLD.id;
        UPDATE audit_table SET
            #list of parameters to audit
            title = OLD.title,
            artist = OLD.artist,
            descr = OLD.descr,
            year = OLD.year,
            year_cmt = OLD.year_cmt,
            type = OLD.type,
            material = OLD.material,
            inside = OLD.inside,
            address = OLD.address,
            county = OLD.county,
            muni = OLD.muni,
            district = OLD.district,
            lat = OLD.lat,
            lon = OLD.lon,
            source = OLD.source,
            official_url = OLD.official_url,
            owner = OLD.owner,
            cmt = OLD.cmt
        WHERE id = OLD.id;
        SET NEW.ugc=1;
    ELSE                    #if an audit post already exists then check if changes have been reverted. If so delete audit
        SELECT created
        FROM audit_table
        WHERE audit_table.id = OLD.id
            #list of parameters to compare
            AND audit_table.title = NEW.title
            AND audit_table.artist = NEW.artist
            AND audit_table.descr = NEW.descr
            AND audit_table.year = NEW.year
            AND audit_table.year_cmt = NEW.year_cmt
            AND audit_table.type = NEW.type
            AND audit_table.material = NEW.material
            AND audit_table.inside = NEW.inside
            AND audit_table.address = NEW.address
            AND audit_table.county = NEW.county
            AND audit_table.muni = NEW.muni
            AND audit_table.district = NEW.district
            AND ((audit_table.lat IS NULL AND NEW.lat IS NULL) OR (audit_table.lat IS NOT NULL AND audit_table.lat = NEW.lat))
            AND ((audit_table.lon IS NULL AND NEW.lon IS NULL) OR (audit_table.lon IS NOT NULL AND audit_table.lon = NEW.lon))
            AND audit_table.source = NEW.source
            AND audit_table.official_url = NEW.official_url
            AND audit_table.owner = NEW.owner
            AND audit_table.cmt = NEW.cmt
        INTO tmp_date;
        IF NOT tmp_date IS NULL THEN
            SET NEW.ugc=0;
            DELETE from audit_table WHERE id = OLD.id;
        END IF;
    END IF;
END;
|
DELIMITER ;
