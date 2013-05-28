#The goals of these views is to give a uniform way of accessing the fields independently of which version of the information is required
#For this reason even the official view contains ugc only fields (albeit blank ones)
#NOte that this might not be desirable due to view tables not being indexed...

#Does not do much but this way we encourage people to go through views
CREATE OR REPLACE VIEW normal_view
AS
SELECT *
FROM main_table m
ORDER BY m.id;

#If ugc flag i on then show audit table instead
CREATE OR REPLACE VIEW official_strict_view
AS
SELECT m.id, 
       IF(m.ugc=1,a.title,m.title) as title, 
       IF(m.ugc=1,a.artist,m.artist) as artist, 
       IF(m.ugc=1,a.descr,m.descr) as descr, 
       IF(m.ugc=1,a.year,m.year) as year, 
       IF(m.ugc=1,a.year_cmt,m.year_cmt) as year_cmt, 
       IF(m.ugc=1,a.type,m.type) as type, 
       IF(m.ugc=1,a.material,m.material) as material, 
       IF(m.ugc=1,a.inside,m.inside) as inside, 
       IF(m.ugc=1,a.address,m.address) as address, 
       IF(m.ugc=1,a.county,m.county) as county, 
       IF(m.ugc=1,a.muni,m.muni) as muni,
       IF(m.ugc=1,a.district,m.district) as district,
       IF(m.ugc=1,a.lat,m.lat) as lat,
       IF(m.ugc=1,a.lon,m.lon) as lon,
       "" as image,
       IF(m.ugc=1,a.source,m.source) as source,
       m.ugc,
       IF(m.ugc=1,a.created,m.changed) as changed,
       m.created,
       "" as wiki_article,
       "" as commons_cat, 
       IF(m.ugc=1,a.official_url,m.official_url) as official_url, 
       IF(m.ugc=1,a.owner,m.owner) as owner, 
       "" as same_as,
       "" as free,
       #"" as free_cmt,
       IF(m.ugc=1,a.cmt,m.cmt) as cmt
FROM main_table m LEFT OUTER JOIN audit_table a
ON m.id = a.id
ORDER BY m.id;

#official view but any blank fields are replaced by ugc material
CREATE OR REPLACE VIEW official_enhanced_view
AS
SELECT m.id, 
       IF(m.ugc=1 AND NOT a.title = "",a.title,m.title) as title, 
       IF(m.ugc=1 AND NOT a.artist = "",a.artist,m.artist) as artist, 
       IF(m.ugc=1 AND NOT a.descr = "",a.descr,m.descr) as descr, 
       IF(m.ugc=1 AND NOT a.year = "0000",a.year,m.year) as year, 
       IF(m.ugc=1 AND NOT a.year_cmt = "",a.year_cmt,m.year_cmt) as year_cmt, 
       IF(m.ugc=1 AND NOT a.type = "",a.type,m.type) as type, 
       IF(m.ugc=1 AND NOT a.material = "",a.material,m.material) as material, 
       IF(m.ugc=1,a.inside,m.inside) as inside, 
       IF(m.ugc=1 AND NOT a.address = "",a.address,m.address) as address, 
       IF(m.ugc=1 AND NOT a.county = "00",a.county,m.county) as county, 
       IF(m.ugc=1 AND NOT a.muni = "0000",a.muni,m.muni) as muni, 
       IF(m.ugc=1 AND NOT a.district = "",a.district,m.district) as district, 
       IF(m.ugc=1 AND NOT a.lat IS NULL,a.lat,m.lat) as lat,
       IF(m.ugc=1 AND NOT a.lon IS NULL,a.lon,m.lon) as lon,
       m.image,
       IF(m.ugc=1,a.source,m.source) as source,
       m.ugc,
       m.changed,
       m.created,
       m.wiki_article,
       m.commons_cat, 
       IF(m.ugc=1 AND NOT a.official_url = "",a.official_url,m.official_url) as official_url, 
       IF(m.ugc=1 AND NOT a.owner = "",a.owner,m.owner) as owner, 
       m.same_as,
       m.free,
       #m.free_cmt,
       IF(m.ugc=1 AND NOT a.cmt = "",a.cmt,m.cmt) as cmt
FROM main_table m LEFT OUTER JOIN audit_table a
ON m.id = a.id
ORDER BY m.id;

