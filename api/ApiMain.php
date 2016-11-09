<?php
    /*
     * Entry point for api
     *
     * To do:
     * help function/default if no params defined
     * move constraint treatment here
     */
    $helpurl='https://se.wikimedia.org/wiki/Offentligkonst.se/Teknisk_dokumentation/Api';

    class ApiMain{
        function search(){
            # Database info (including username+pass) in external file
            if ( file_exists('/home/andre/config.php')){
                require_once('/home/andre/config.php');
            } elseif (file_exists('config.php')){
                require_once('config.php');
            } else {
                die( 'Couldn\'t find config file ');
            }

            include('Format.php');       #formats the output
            include('ApiBase.php');      #functions used by multiple modules
            include('ApiGet.php');       #standard sql query stuff
            include('ApiStats.php');     #stats about the database
            include('ApiAdmin.php');     #various functions that the average user wouldn't care about
            include('ApiArtist.php');    #hook into the artist_table
            #include('ApiHelp.php');     #help file/documentation
            global $helpurl;

            /*
             * Trying to connect to mysql server and database
             * Output Temporary error if unable to.
             */
            if(!@mysql_connect($dbServer,$dbUser,$dbPassword)){
                $results = ApiBase::makeErrorResult(
                '500',
                'Temporary Error. '.
                            'Our server might be down, please try again later.['.mysql_error().']',
                null);
                $errors=1;
            }
            if(!@mysql_select_db($dbDatabase)){
                $results = ApiBase::makeErrorResult(
                '500',
                'Temporary Error. '.
                            'Our server might be down, please try again later.['.mysql_error().']',
                null);
                $errors=1;
            }

            /*
             * Set up jsonp compatibility
             */
            if(strtolower($_GET['format']) == 'jsonp'){
                if(!isset($_GET['callback'])){
                    $results = ApiBase::makeErrorResult(
                    '640',
                    'JSONP Error. '.
                                'Cannot request JSONP without a callback',
                    null);
                    $errors=1;
                }
            }


            /*
             * If no errors were found during connection
             * let's proceed with our queries
             */
            if(!$errors){
                mysql_query("SET CHARACTER SET utf8");

                #deal with general constraints
                try{
                    $constraints = ApiBase::readConstraints();
                }catch (ValueLimitException $e) {
                    $results = ApiBase::makeErrorResult(
                    '602',
                    $e->getMessage(),
                    null);
                    $errors=1;
                }catch (CharacterLimitException $e) {
                    $results = ApiBase::makeErrorResult(
                    '603',
                    $e->getMessage(),
                    null);
                    $errors=1;
                }catch (Exception $e) {
                    $results = ApiBase::makeErrorResult(
                    '600',
                    $e->getMessage(),
                    null);
                    $errors=1;
                }
                #if kml/geojson output format then make sure has_coords is set
                if(($_GET['format']=='kml' or $_GET['format']=='geojson') and !isset($_GET['has_coords'])){
                    $constraints['coords'] = ApiBase::requireCoords();
                }
            }
            if(!$errors){
                #switch by action; return results array
                switch (strtolower($_GET['action'])) {
                    case 'get':
                        $results = ApiGet::run($constraints);
                        break;
                    case 'artist':
                        $results = ApiArtist::run($constraints);
                        break;
                    case 'statistics':
                        /*
                         * Outputs counts per table/muni/county/artist/withCoords/withPics
                         */
                        $results = ApiStats::run($constraints);
                        break;
                    case 'admin':
                        /*
                         * should generate a file with changes (since a certain date) and/or
                         * list all entries (with changes) from a given source which has ugc=1.
                         * Possibly use this to create an rss feed?
                         */
                        $results = ApiAdmin::run($constraints);
                        break;
                    case 'help':
                        header( 'Location: '.$helpurl ) ;
                        break;
                    default:
                        $results = ApiBase::makeErrorResult(
                                    '601',
                                    'Action Failed. '.
                                        'Sorry but "'.$_GET['action'].'" is not a valid action for this api.',
                                    $warning
                                    );
                        break;
                }
            }

            /* Switch between output formats */
            if(isset($_GET['format'])){
                switch (strtolower($_GET['format'])) {
                    case 'xml' :
                        Format::outputXml($results);
                        break;
                    case 'json' :
                        Format::outputJson($results);
                        break;
                    case 'php' :
                        Format::outputPhp($results);
                        break;
                    case 'kml' :
                        Format::outputKml($results);
                        break;
                    case 'xsl' :
                        Format::outputXsl($results);
                        break;
                    case 'wiki' :
                        Format::outputWiki($results);
                        break;
                    case 'geojson' :
                        Format::outputGeojson($results);
                        break;
                    case 'jsonp' :
                        Format::outputJsonp($results, $_GET['callback']);
                        break;
                    default:
                        $results['head']['warning'] .= 'You chose an output format ['.$_GET['format'].'] which does not exist ; defaulting to xml. ';
                        Format::outputDefault($results);
                };
            }else{
                if(isset($_GET['callback'])){
                    Format::outputJsonp($results, $_GET['callback']);
                }
                else {
                    Format::outputDefault($results);
                }
            }

            mysql_close();
        }
    }
?>
