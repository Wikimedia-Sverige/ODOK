Introduction
------------

The api can be accessed at <http://offentligkonst.se/api/api.php?>. In
the examples below this part of the url is simply abbreviated to
[api.php?](http://offentligkonst.se/api/api.php?).

The two main parameters for the api are:

-   `action` - What action you would like to perform.
    -   This takes one of four values: `get, statistics, admin` or
        `help`. Defaults to `help`. More info
        [below](#Actions "wikilink").
-   `format` - Which format would you like the response in. More info in
    [output formats](#Output_formats "wikilink") below.

Several of the actions also allow you to specify constraints on which
information is returned. You can read more about these under
[Constraints](#Constraints "wikilink") below.

![note](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pictogram_voting_comment.svg/18px-Pictogram_voting_comment.svg.png)
Note that if the same parameter is added twice then only the latter is
considerer. Where allowed multiple values for the same parameters are
separated by the pipe "|" symbol.

![note](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pictogram_voting_comment.svg/18px-Pictogram_voting_comment.svg.png)
Note that you can add a maximum of 50 values per parameter per search.

Some api actions limit the number of results returned. For these the
call also accepts the following parameters:

-   `limit`: The maximum number of results returned [integer in the
    range 1-100], defaults to 10;
-   `offset`: From which result to start returning the results (used in
    conjuncture with the continue header, see below) [positive integer],
    defaults to 0.

Example:

-   [api.php?action=get&format=xsl&limit=15&offset=5](http://offentligkonst.se/api/api.php?action=get&format=xsl&limit=15&offset=5)

### Response

The format of the response is controlled using the
[`format`](#Output_formats "wikilink") parameter. Although the output
varies depending on the api call the basic structure remains the same.
The output contains a *body* carrying the bulk of the data and a
*header* which contains at least one field:

-   `success`: This indicates whether the api call was successful (1) or
    whether it [encountered an error](#Errors "wikilink") (0).

Additionally the header may contain more fields.

-   `warning`: This field is included if a non-critical error occurred.
    These are normally related to one or more of the parameters being
    miss-formatted.

In the cases where the api call accepts the `limit` and `offset`
parameters the header will also contain the following:

-   `hits`: A numbering of the returned hits. In the format "*offset* –
    *offset + \#displayed\_results* of *\#total\_results*;
-   `limit`: The limit used in the api call.
-   `continue`: If there are more results still to display then this
    gives the value of the next `offset`.

### Errors

If the api call encounters an error the header will (in addition to
`success=0`) also contain an [`error_number`](#Error_Codes "wikilink")
as well as an `error_message` which tries to describe, in words, what
went wrong. The body of the response is left empty.

#### Error Codes

-   500 - (apiMain.php) can't connect to server or database
-   600 - (apiMain.php) readConstraints doQuery (i.e. mySQL lookup)
    failed
-   601 - (apiMain.php) action not recognised
-   602 - (apiMain.php) readConstraints, to many values given for a
    single parameter
-   603 - (apiMain.php) readConstraints, to many characters in the
    values of a single parameter (see
    [1](http://stackoverflow.com/questions/7724270/max-size-of-url-parameters-in-get))
-   610 - (ApiGet.php) doQuery failed
-   620 - (ApiStats.php) doQuery failed
-   630 - (ApiAdmin.php) doQuery failed
-   631 - (ApiAdmin.php) info without id or table
-   632 - (ApiAdmin.php) function not recognised

### Constraints

A general constraints is one which can be applied to either the get or
the statistics module. There are also additional constraints which are
applied to the artist module. The constraints are split into five types:

#### Exact Parameters

These will return results only when the entered value matches the result
exactly. Multiple values are separated by pipes '|'. These parameters
are:

-   (general) `id`, `type`, `county`, `muni`, `district`, `source`,
    `wiki`, `list`, `commons_cat`, `official_url`, `free`, `owner`,
    `county_name` and `muni_name`;
-   (artist) `id`, `wiki` and `last_name`.

Most of these are self explanatory. Note however the following:

-   `muni`: this is the (4-digit) municipal code, to restrict by name
    use `muni_name` instead (without "kommun", e.g. "Lund" instead of
    "Lunds kommun").
-   `county`: this is the county code (one or two upper case letters),
    to restrict by name use `county_name` instead.
-   `wiki` and `list`: this is the wikidata entity. i.e something like
    "Q1234".
-   `free`: this only takes the values 'pd','cc','unfree' and ''.

![note](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pictogram_voting_comment.svg/18px-Pictogram_voting_comment.svg.png)
You cannot use both the `muni` parameter and the `muni_name` parameter
as doing so will not give the expected result. The same is true for the
`county/county_name` parameters.

Example:

-   [api.php?action=get&muni=1281|0180&source=SKB](http://offentligkonst.se/api/api.php?action=get&muni=1281|0180&source=SKB)

#### Soft Parameters

These are parameters which use wild-card searches. E.g. "ello" will give
a hit for any value of the form "%ello%" where % can be any string. I.e.
a hit on either of ("ello", "hello", "elloy", "mellow yellow"). These
parameters are:

-   (general) `title`, `artist` and `address`;
-   (artist) `first_name` and `name`.

#### Boolean Parameters

These are parameters that take only the values "`true`" or "`false`".
These parameters are:

-   (general) `is_inside`, `is_removed`, `has_ugc`, `has_image`,
    `has_coords`, `has_wiki`, `has_list`, `has_cmt` and `has_same`
    (i.e. has `same_as`);
-   (artist) `is_dead`.

#### Ranged Parameters

These are parameters where you might want to specify a numerical range
of (temporal) values rather than a specific one. These parameters are:

-   (general) `year`, `changed` and `created`;
-   (artist) `birth_year`, `death_year` and `lifespan`.

These parameters work by accepting either one parameter or two
parameters separated by a pipe "|". If only one value is given the
parameter behaves as an [exact parameter](#Exact_Parameters "wikilink").
If two values are given then any result between the two values are
returned. If the second value is left out then results larger than the
first value are returned. If the first value is left out then results
smaller than the second value are returned. All three ranges include the
end-point(s).

As a summarising example:

-   `year=1980` : Returns only results where year = 1980
-   `year=1980|` : Returns results where year ≥ 1980
-   `year=1980|1990` : Returns results where 1980 ≤ year ≤ 1990
-   `year=|1980` : Returns results where year ≤ 1980

![note](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pictogram_voting_comment.svg/18px-Pictogram_voting_comment.svg.png)
As a result these parameters do not accept multiple values in the normal
sense.

![note](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pictogram_voting_comment.svg/18px-Pictogram_voting_comment.svg.png)
"lifespan" does not support an exact year but must be given an (open or
closed) span.

The `created` and the `changed` parameters refer to when the object was
first introduced into the database and when it was last changed. These
can be specified at three levels

1.  Year: You may specify a year in the format `YYYY`.
2.  Date: Specify a date in the format `YYYYMMDD`.
3.  Time: Specify a time in the format `YYYYMMDDHHMMSS`.

#### Bounding Box

This creates a geographical constraint where only coordinates within a
certain box are returned. The constraint is formatted as:

-   (general) `bbox=bl_lon|bl_lat|tr_lon|tr_lat`

where bl = bottom left, tr = top right, lat=latitude and lon=longitude.

![note](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pictogram_voting_comment.svg/18px-Pictogram_voting_comment.svg.png)
Note that coordinates must be given in decimal notation (using "." as
the decimal separator).

### Output formats

The available output formats that can be specified through the `format`
parameter are:

-   `xml`: (default)
    -   `xsl`: style-sheet wrapper for xml (limited to `action=get`,
        `action=artist` and `action=admin` with either `function=diff`
        or `function=info`)
-   `json` - *pretty print* json
    -   add `json=compact` for compact format json
-   `php`: serialized php
-   `wiki`: a list of row-templates for Wikipedia designed using the
    [Offentligkonstlista](:w:sv:Mall:Offentligkonstlista "wikilink")-template
    on sv.wikipedia

Map formats

-   `geojson`: *pretty print* geojson with all parameters as properties
    -   add `json=compact` for compact format json
    -   add `geojson=full` for a version which more in-depth information
        such as grouping of properties, look-up of `artist_table`,
        look-up of sv.wp articles corresponding to given wikidata id.
        Note that this output is significantly slower.
-   `kml`: creates a static kml file for map visualisation. Note that
    e.g. google maps will display a cached version of this file
-   `dynamickml`: creates a dynamic kml file for map visualisation.
    Unlike the static version this is not cached by e.g. google maps. As
    you move around on the map the bbox parameter will automatically
    update.
-   `googlemaps`: opens the above dynamic kml file directly in google
    maps centred, and zoomed in, on Sweden (for `action=get` only)
    -   All map formats are limited to `action=get` only
    -   All map formats sets the `has_coords` constraint (to `true`) if
        this constraint isn't specified beforehand.

Examples:

-   [api.php?action=statistics&format=json](http://offentligkonst.se/api/api.php?action=statistics&format=json)
-   [api.php?action=admin&function=diff&changed=20130316|](http://offentligkonst.se/api/api.php?action=admin&function=diff&changed=20130316|)
-   [api.php?action=get&format=googlemaps&limit=10](http://offentligkonst.se/api/api.php?action=get&format=googlemaps&limit=10)

Example outputs can be seen at [/output](/output "wikilink").

Actions
-------

### action=get

Performs a standard SQL query on the main table of the database based on
given constraints.

In addition to the ordinary constraints and parameters this module also
listens for the following parameter:

-   `view`: the [view](../Databas "wikilink") used
    [`strict`, `enhanced`, `normal`], defaults to normal.
-   `show`: the parameters to show
    [`id`, `title`, `artist`, `descr`, `year`, `year_cmt`, `type`,
    `material`, `inside`, `address`, `county`, `muni`, `district`, `lat`,
    `lon`, `removed`, `image`, `source`, `ugc`, `changed`, `created`,
    `wiki`, `list`, `commons_cat`, `official_url`, `same_as`, `free`,
    `cmt`, `owner`], defaults to showing all. (pipe-separated)

Examples:

-   [api.php?action=get&view=enhanced&limit=10&show=title|muni|image|artist](http://offentligkonst.se/api/api.php?action=get&view=enhanced&limit=10&show=title|muni|image|artist)
-   [api.php?action=get&has\_image=true](http://offentligkonst.se/api/api.php?action=get&has_image=true)

### action=artist

Performs a standard SQL query on the artist_table of the database based
on given constraints.

This action allows the artist(s) to be selected using either of:

-   `artwork`: The id of an artwork, or a pipe-separated list of ids.
    Will return all artists which were involved with any of the listed
    works.
-   A combination of `id`, `wiki`, `first_name`, `last_name`, `name`,
    `birth_year`, `death_year`, `is_dead`, `lifespan`.
        -   "lifespan" is a [ranged parameter](#Ranged Parameters) where
            the whole of the artists lifespan must fit in the given range;
        -   "name" is a [soft parameter](#Soft Parameters)searching
            against a combination of first and last name.

In addition to the ordinary constraints and parameters this module also
listens for the following parameter:

-   `show`: the parameters to show
    [`id`, `first_name`, `last_name`, `wiki`, `birth_date`, `birth_year`,
    `death_date`, `death_year`, `creator`, `changed`, `works`], defaults
    to showing all. (pipe-separated)
        -   "creator" is the corresponding creator template on Wikimedia
            Commons;
        -   "works" are a list of all of the works by the artist found
            in the database.

![note](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pictogram_voting_comment.svg/18px-Pictogram_voting_comment.svg.png)
You cannot combine the `artwork` parameter with any other constraint
(but it can be combined with the `show` parameter).

Examples:

-   [api.php?action=artist&limit=10&is_dead=true&show=wiki|first_name|last_name|works](http://offentligkonst.se/api/api.php?action=artist&limit=10&is_dead=true&show=wiki|first_name|last_name|works)
-   [api.php?action=artist&name=Milles&lifespan=1850|1950](http://offentligkonst.se/api/api.php?action=artist&name=Milles&lifespan=1850|1950)
-   [api.php?action=artist&artwork=k1281-LjG/02](http://offentligkonst.se/api/api.php?action=artist&artwork=k1281-LjG/02)

### action=statistics

Gives statistics about the database. The two
existing stats to look at are determined by whether the "table" or "column"
parameters are set. Additionally you can break down the result using the
split parameter:

-   `table`: This will give you the number of entries in a given table.
    [`all`, `main`, `artist`, `audit`, `county`, `muni`, `source`,
    `ugc`, `aka`], defaults to all. (pipe-separated)
    -   Note that tables other than main or audit will ignore any
        additional constraints
-   `column`: Shows the number of items in the main table where the
    given column is non-zero
    [`id`, `title`, `artist`, `descr`, `year`, `year_cmt`, `type`,
    `inside`, `address`, `county`, `muni`, `district`, `lat`, `lon`,
    `removed`, `image`, `source`, `ugc`, `changed`, `created`, `wiki`,
    `list`, `commons_cat`, `official_url`, `same_as`, `free`, `cmt`,
    `owner`], no default. (pipe-separated)
-   `split`: Shows the result broken down by municipality, county or
    source [`muni`, `county`, `source`], no default.
    -   Note that split will not work on either multiple tables or
        columns nor for tables other than main or audit.

The body of the response changes depending on the options but takes the
following general shapes:

-   `table` : table\_name -> count
-   `column`: column\_name -> count
-   `split`:
    split\_type -> [split\_name -> value, table/column\_name -> count]
    -   e.g. muni -> [muni\_name -> "Lund", "main" -> "4"]

Examples:

-   [api.php?action=statistics&table=main|audit](http://offentligkonst.se/api/api.php?action=statistics&table=main|audit)
-   [api.php?action=statistics&column=muni&county=M](http://offentligkonst.se/api/api.php?action=statistics&column=muni&county=M)
-   [api.php?action=statistics&column=image&split=county](http://offentligkonst.se/api/api.php?action=statistics&column=image&split=county)

### action=admin

Includes some maintenance functions that will not be
of interest to the average user.

To use set the `function` parameter to one of:

-   `info`: Displays all known info for a given object as identified by
    its id and table
-   `diff`: produces a list of changes in main\_table wrt. audit\_table
    (listens for global constraints)
-   `objectlessArtist`: produces a list of artists that have no objects
-   `yearlessArtist`: produces a list of artists that have no
    death\_year and where birth\_year is also missing or occurred more
    than 100 years ago
-   `artistlessObject`: produces a list of objects that have no linked
    artists

Examples:

-   [api.php?action=admin&function=info&table=main&id=1](http://offentligkonst.se/api/api.php?action=admin&function=info&table=main&id=1)
-   [api.php?action=admin&function=diff&changed=20130319|](http://offentligkonst.se/api/api.php?action=admin&function=diff&changed=20130319|)
-   [api.php?action=admin&function=artistlessObject](http://offentligkonst.se/api/api.php?action=admin&function=artistlessObject)
