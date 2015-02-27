<?php
    /*
     * General functions used by various classes (but unrelated to formating)
     * 
     * Standardised output arrays:
     *     makeErrorResult/makeSuccessResult/makeSuccessResultHead:
     *         returns a correctly formated array for furhter
     *         treatment by the Format class
     * 
     * Query related functions:
     *     doQuery:
     *         performs a query returning the rows or throwing an exception
     *     addConstraint:
     *         adds array of (pipe-separated) constraints to a query
     *     notEmpty:
     *         adds (pipe separated) column-not-empty constraints to a query
     * 
     * Constraint/Parameter related functions:
     *     readConstraints: 
     *         reads in a list of general constraints and classiifes them by type
     *     available types (functions) are 
     *         bboxParam, rangedParam, namedParam, boolParam, softParam
     * 
     * Interactions with other tables
     *     getAdminNames:
     *         returns a list with id-name for eiter muni or county
     *     getArtistInfo:
     *         returns a list of artists for a given id
     * 
     * General functions
     *     getImageFromCommons:
     *         returns the thumbnail url for a comons image
     *     getArticleFromWikidata:
     *         returns an array of wikidataID-svwikiURLs (performs an api request, beware of delays, max limits etc.)
     */

    class ApiBase{
        /*
         * Produce standardised output arrays
         */
        function makeErrorResult($error_num, $error_msg, $warning){
            #global $helpurl;
            $results['head'] = Array(
                            'status' => '0',
                            'error_number'  => $error_num, 
                            'error_message' => $error_msg.' For documentation please consult action=help.'
                    );
            if (!empty($warning))
                $results['head']['warning'] = $warning;
            $results['body'] = Array();
            #$results['body'] = $helpurl;#Could include help or helplink here
            return $results;
        }
        function makeSuccessResult($warning, $body){
            $results['head'] = Array(
                            'status' => '1'
                        );
            if (!empty($warning))
                $results['head']['warning'] = $warning;
            $results['body'] = $body;
            #echo(print_r($results));
            return $results;
        }
        #same as makeSuccessResult() but more parameters than the warning may be passed to the header
        function makeSuccessResultHead($head, $body){
            $results['head'] = Array(
                        'status' => '1'
                    );
            if (!empty($head)){
                $results['head'] += $head;
            }
            $results['body'] = $body;
            #echo(print_r($results));
            return $results;
        }
        #display bitwise operators [bit(1) in sql] as numbers
        function sanitizeBit1($array){
            $bitParams = Array('ugc', 'inside', 'real_id');
            foreach ($bitParams as $bp){
                if (in_array($bp, array_keys($array)))
                    $array[$bp] = ord($array[$bp]);
            }
            return $array;
        }
        #mod to the above for the admin/diff output
        function sanitizeBit1diff($array){ 
            $bitParams = Array('ugc', 'inside', 'real_id');
            foreach ($bitParams as $bp){
                if (in_array('m_'.$bp, array_keys($array))){
                    $array['m_'.$bp] = ord($array['m_'.$bp]);
                    $array['a_'.$bp] = ord($array['a_'.$bp]);
                }
            }
            return $array;
        }
        
        /*
         * Query related functions
         */
        #given a query it returns resulting rows or throws an exception containing the mysql_error
        function doQuery($query){
            if($_GET['debug']=='true'){
                echo($query);
            }
            if(!@$go = mysql_query($query)){
                throw new Exception(mysql_error());
            } else {
                while ($row = mysql_fetch_assoc($go)){
                    $rows[] = $row;
                }
                return $rows;
            }
        }
        
        #adds constraints to a query (also deals with the output of readConstraints() )
        #prefix allows to specify which table
        function addConstraints($query, $constraints, $prefix = ''){
            foreach($constraints as $key => $value){
                switch ($key){
                    case 'bbox':
                    case 'BBOX':
                    case 'year':
                    case 'changed':
                    case 'created':
                    case 'image':
                    case 'coords':
                    case 'cmt':
                    case 'inside':
                    case 'ugc':
                    case 'artist':
                    case 'title':
                    case 'address':
                    case 'wiki':
                    case 'same':
                        #these are already in mysql format
                        $query .= $value.'
                AND '.$prefix;
                        break;
                    default: #(pipe separated) constraints
                        $v = explode('|', $value);
                        if (count($v)==1){
                            $query .= '`'.mysql_real_escape_string($key).'` = "'.mysql_real_escape_string($value).'"
                AND '.$prefix;
                        }else{
                            $query .= '`'.mysql_real_escape_string($key).'` IN ("'.implode('" , "', array_map('mysql_real_escape_string', $v)).'")
                AND '.$prefix;
                        }
                }
            }
            $query = substr($query, 0, -strlen('AND '.$prefix));    #killing the last AND
            return $query;
        }
        #adds (pipe separated) column-not-empty constraints to a query
        function notEmpty($query, $columns){
            $cols = explode('|', $columns);
            foreach($cols as $column){
                switch ($column){
                    case 'lat':
                    case 'lon':
                    case 'year':
                        $query .= '`'.mysql_real_escape_string($column).'` IS NOT NULL
                AND ';
                        break;
                    case 'ugc':
                        $query .= '`'.mysql_real_escape_string($column).'` != "0"
                AND ';
                        break;
                    case 'coords':
                        $query .= '`lat` IS NOT NULL AND `lon` IS NOT NULL
                AND ';
                        break;                                  
                    default:
                        $query .= '`'.mysql_real_escape_string($column).'` != "" 
                AND ';
                }
            }
            $query = substr($query, 0, -strlen('AND '));    #killing the last AND
            return $query;
        }
        
        /* Read in limit (must be in range 1-100, defaults to 10)*/
        function setLimit($lim){
            $max_limit = 100;
            $min_limit = 1;
            $default_limit = 10;
            $limit = isset($lim) ? intval($lim) : $default_limit;
            if (!empty($lim) and !is_numeric($lim)){
                $warning = 'Limit must be a number; your limit was changed from "'.$lim.'" to '.$default_limit.'. ';
                $limit = $default_limit;
            }
            elseif ($limit>$max_limit){
                $warning = 'Max limit is '.$max_limit.'; your limit was changed from "'.$limit.'" to '.$max_limit.'. ';
                $limit = $max_limit;
            }elseif ($limit<$min_limit){
                $warning = 'Minimum limit is '.$min_limit.'; your limit was changed from "'.$limit.'" to '.$min_limit.'. ';
                $limit = $min_limit;
            } 
            return Array($limit, $warning);
        }
        /* Read in offset (must be >=0, defaults to 0)*/
        function setOffset($off){
            $default_off = 0;
            $min_off = 0;
            $offset = isset($off) ? intval($off) : $default_off;
            if (!empty($off) and !is_numeric($off)){
                $warning = 'Offset must be a number; your offset was changed from "'.$off.'" to '.$default_off.'. ';
                $offset = $default_off;
            }elseif ($offset<$min_off){
                $warning = 'Minimum offset is '.$min_off.'; your offset was changed from "'.$offset.'" to '.$min_off.'. ';
                $offset = $min_off;
            } 
            return Array($offset, $warning);
        }
        /* Test if any of the parameters is to large for $_GET to handle */
        function largeParam(){
            $maxChar = 512;
            $queries = explode('&', $_SERVER['QUERY_STRING']);
            foreach ($queries as $q) {
                $v = explode('=',$q);
                $v[1] = strlen(urldecode($v[1]));
                if ($v[1]>$maxChar){
                    throw new CharacterLimitException('Each parameter must be no more than ' .$maxChar. ' bytes. The parameter "' .$v[0]. '" was ' .$v[1]. ' bytes.');
                }
            }
        }
        #reads in paramters to deal with constraints
        /* NOTE: 
         *    if someone adds two params with same name then only the last one is considered
         *    This also applies to muni/county with muni_name/county_name as they fill the same parameter
         * TO DO:
         *    wildcard/keyword searches (in e.g. descr)
         */
        function readConstraints(){
            #define list of allowed generic constraints
            #Should material be added (if so it's soft)? Left out for now due to municipal concerns
            $allowed = Array('id', 'title', 'artist', 'year', 'type', 'address', 
                             'county', 'muni', 'county_name', 'muni_name', 
                             'district', 'bbox', 'BBOX', 'source', 'changed',
                             'created', 'wiki_article', 'commons_cat',
                             'official_url', 'free', 'owner', 'has_cmt',
                             'is_inside', 'has_ugc', 'has_image', 'has_coords',
                             'has_wiki', 'has_same');
            $maxValues = 50;
            try{
                ApiBase::largeParam();
            }catch (Exception $e){throw $e;}
            if(empty($_GET))
                return null;
            else{
                try{
                    foreach ($_GET as $key => $value){
                        if(empty($value)){
                            continue;
                        }
                        elseif (!in_array($key, $allowed)){
                            continue;
                        }
                        elseif (substr_count($value, '|') > $maxValues){
                            throw new ValueLimitException('You can enter a maximum of '. $maxValues .' values per parameter (you entered '. substr_count($value, '|') .' values for the parameter "'. $key .'").');
                            continue;
                        }
                        switch ($key){
                        case 'BBOX': #dynamicKml gives comma separated bbox
                            $value = implode('|',explode(',', $value));
                        case 'bbox':
                            $params[$key] = self::bboxParam($key, $value);
                            break;
                        case 'year':
                        case 'created':
                        case 'changed':
                            $params[$key] = self::rangedParam($key, $value);
                            break;
                        case 'muni_name':
                        case 'county_name':
                            $keyparts = explode('_', $key);
                            $params[$keyparts[0]] = self::namedParam($keyparts[0], $value);
                            break;
                        case 'is_inside':
                        case 'has_ugc':
                        case 'has_coords':
                        case 'has_cmt':
                        case 'has_image':
                        case 'has_wiki':
                        case 'has_same':
                            $val = self::boolParam($key, $value);
                            if (!empty($val)){
                                $keyparts = explode('_', $key);
                                $params[$keyparts[1]] = $val;
                            }
                            break;
                        case 'artist':
                        case 'title':
                        case 'address':
                            $params[$key] = self::softParam($key, $value);
                            break;
                        default:
                            $params[$key] = $value;
                            break;
                        }
                    }
                }catch (Exception $e){throw $e;}
            return $params;
            }
        }
        #search by municipal/county name requires there to be a lookup so as to identify id numbers
        #misspelt names are ignored
        private function namedParam($table, $value){
            $vArray = explode('|', $value);
            #remove any empty parameters
            $i=0;
            foreach($vArray as $v){
                if (empty($v)){
                    unset($vArray[$i]);
                }
                $i++;
            }
            if (!empty($vArray)){ #since all elements may have been removed
                $query = 'SELECT `id`, `name`
            FROM `'.mysql_real_escape_string($table).'_table`
            WHERE `name` IN ("'.implode('" , "', array_map('mysql_real_escape_string', $vArray)).'")
            ';
                try{
                    $response = ApiBase::doQuery($query);
                }catch (Exception $e) {throw $e;}
                foreach($response as $r)
                    $ids[] = $r['id'];
                return implode('|', $ids);
            }
        }
        /*a parameter which allows a (numeric)range to be specified.
         *  if one parameter then exact.
         *  if two then from|to,
         *  if more then wrong
         */
        private function rangedParam($key, $value){
            $validSizes = Array(4,8,14); # YYYY, YYYYMMDD, YYYYMMDDHHMMSS
            $vArray = explode('|', $value);
            foreach ($vArray as $v)
                if (!empty($v) and !is_numeric($v)){
                    $errors = true;
                    throw new Exception('The "'.$key.'" parameter was formatted illegally (must be numeric). ');
                    continue;
                }
                elseif (!empty($v) and !in_array(strlen((string)$v),$validSizes)){
                    $errors = true;
                    throw new Exception('The "'.$key.'" parameter was formatted illegally (must be in one of the following formats: YYYY, YYYYMMDD, YYYYMMDDHHMMSS). ');
                    continue;
                }
            if (!$errors){
                if (count($vArray)==1)
                    return '`'.mysql_real_escape_string($key).'` = "'.mysql_real_escape_string($vArray[0]).'"';
                elseif (count($vArray)==2){
                    if ( empty($vArray[0]) and !empty($vArray[1]) )
                        return '`'.mysql_real_escape_string($key).'` <= "'.mysql_real_escape_string($vArray[1]).'"';
                    elseif ( !empty($vArray[0]) and empty($vArray[1]) )
                        return '`'.mysql_real_escape_string($key).'` >= "'.mysql_real_escape_string($vArray[0]).'"';
                    elseif ( !empty($vArray[0]) and !empty($vArray[1]) )
                        return '`'.mysql_real_escape_string($key).'` BETWEEN "'.mysql_real_escape_string($vArray[0]).'" AND "'.mysql_real_escape_string($vArray[1]).'"';
                    else
                        throw new Exception('The "'.$key.'" parameter was formatted illegally (both values were empty). ');
                } else
                    throw new Exception('The "'.$key.'" parameter was formatted illegally (too many values). ');
            }
        }
        #creates a mapconstraint based on bbox=bl_lon|bl_lat|tr_lon|tr_lat
        #bl = bottom left, tr = top right, note that coords must be given wit "." as decimal
        private function bboxParam($key, $value){
            $vArray = explode('|', $value);
            if(count($vArray)!=4){
                $errors = true;
                throw new Exception('The "'.$key.'" parameter was formatted illegally (needs 4 values). ');
            }
            if (!$errors){
                foreach($vArray as $v)
                    if (empty($v) or !is_numeric($v)){
                        $errors = true;
                        throw new Exception('The "'.$key.'" parameter was formatted illegally (needs numerical values). ');
                        continue;
                    }
                    else
                        $coords[] = floatval( $v );
            }
            if (!$errors AND ( $coords[1]> $coords[3] OR $coords[0] > $coords[2] ) ) {
                $errors = true;
                throw new Exception('The "'.$key.'" parameter speciifed an invalid bounding box. ');
            }
            if (!$errors){
                $txt =      '`lat` BETWEEN "'.mysql_real_escape_string($coords[1]).'" AND "'.mysql_real_escape_string($coords[3]).'" AND ';
                return $txt.'`lon` BETWEEN "'.mysql_real_escape_string($coords[0]).'" AND "'.mysql_real_escape_string($coords[2]).'"';
            }
        }
        #a soft/wildcard parameter
        private function softParam($key, $value){
            $vArray = explode('|', $value);
            if(count($vArray)>1){
                $errors = true;
                throw new Exception('The "'.$key.'" parameter was formatted illegally (only accepts one value). ');
            }
            if (!$errors)
                return '`'.mysql_real_escape_string($key).'` LIKE "%'.mysql_real_escape_string($value).'%" ';
        }
        #a boolean parameter (true/false needed since 0 isn't passed properly)
        private function boolParam($key, $value){
            if($value != 'true' and $value != 'false'){
                throw new Exception('The "'.$key.'" parameter was formatted illegally (must be "true" or "false"). ');
            }
            else{
                list(,$key) = explode('_', $key);
                switch ($key){
                    case 'cmt':
                    case 'image':
                        if ($value=='false')
                            return '`'.mysql_real_escape_string($key).'` = ""';
                        else
                            return '`'.mysql_real_escape_string($key).'` != ""';
                        break;
                    case 'wiki':
                        if ($value=='false')
                            return '`wiki_article` = ""';
                        else
                            return '`wiki_article` != ""';
                        break;
                    case 'same':
                        if ($value=='false')
                            return '`same_as` IS NULL';
                        else
                            return '`same_as` IS NOT NULL';
                        break;
                    case 'coords':
                        if ($value=='false')
                            return '(`lat` IS NULL OR `lon` IS NULL)'; #bracket to contain the or 
                        else                
                            return '`lat` IS NOT NULL AND `lon` IS NOT NULL';
                        break;
                    default:
                        # 'ugc', 'inside':
                        #these should have bit(1) parameters
                        if ($value=='false')
                            return '`'.mysql_real_escape_string($key).'` = "0"';
                        else                
                            return '`'.mysql_real_escape_string($key).'` = "1"';
                }
            }
        }
        #A wrapper function for setting has_coords constraint outside of the normal procedure
        function requireCoords(){
            return self::boolParam('has_coords', 'true');
        }
        /*
         * End of parameter/constraint code
         */
         
        /*
         * Interactions with other tables
         */
         #returns a list of muni names and id's
        private function getAdminNames($admin){
            $query = 'SELECT id, name FROM `'.mysql_real_escape_string($admin).'_table`';
            $rows = self::doQuery($query);
            $names = Array();
            foreach ($rows as $r)
                $names[$r['id']] = $r['name'];
            return $names;
        }
        function getMuniNames(){
            return self::getAdminNames('muni');
        }
        function getCountyNames(){
            return self::getAdminNames('county');
        }
        #gets the artist info (possibly several) for a given object id
        function getArtistInfo($id){
            if(is_array($id)){
                $idQuery = 'IN (';
                foreach ($id as $i)
                    $idQuery .= '"'.mysql_real_escape_string($id).'", "';
                $idQuery = substr($idQuery, 0, -strlen(', "')); #remove trailing ', "'
            }
            else
                $idQuery = '= "'.mysql_real_escape_string($id).'"';
            $query = 'SELECT CONCAT_WS(" ", first_name, last_name) AS name, wiki FROM `artist_table` WHERE id IN';
            $query .='   (SELECT artist FROM `artist_links` WHERE artist_links.object '.$idQuery.')';
            return self::doQuery($query);
        }
        
        /* 
         * Given the filename on Commons this returns the url of the
         * thumbnail of the given size
         */
        function getImageFromCommons($filename, $size) {
            if ($filename and $size) {
                $filename = ucfirst($filename);
                $filename = str_replace(' ', '_', $filename);
                $url = "https://commons.wikimedia.org/w/thumb.php?f=" . $filename . "&width=" . $size;
                return $url;
            }
        }
        /* gets the data from a URL */
        function get_curl_data($url) {
            $ch = curl_init();
            $timeout = 5;
            curl_setopt($ch, CURLOPT_URL, $url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
            curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, $timeout);
            curl_setopt($ch,CURLOPT_USERAGENT,'Odok-database');
            $data = curl_exec($ch);
            curl_close($ch);
            return $data;
        }
        #Given a wikidata ID this returns the url (for the svwiki article)
        #returns an array if given an array otherwise only the id
        function getArticleFromWikidata($entity, $getUrl=true) {
            if ($entity) {
                if(is_array($entity)){
                    $elist ='';
                    foreach ($entity as $e)
                        $elist .= $e.'|';
                    $elist = substr($elist, 0, -1); #removing trailing '|'
                }else
                    $elist = $entity;
                $apiurl = 'http://www.wikidata.org/w/api.php';
                $queryUrl = $apiurl.'?action=wbgetentities&format=php&ids='.$elist.'&props=sitelinks%2Furls';
                $page = ApiBase::get_curl_data($queryUrl);
                if ( is_null($page) )
                    return null;
                else{
                    $response = unserialize($page);
                    if($response['success']==1){
                        if(!is_array($entity)){
                            if($getUrl)
                                return 'https:'.$response['entities'][ucfirst($entity)]['sitelinks']['svwiki']['url'];
                            else
                                return $response['entities'][ucfirst($entity)]['sitelinks']['svwiki']['title'];
                        }else{
                            $eArray=Array();
                            foreach ($entity as $e){
                                if($getUrl)
                                    $eArray[$e] = 'https:'.$response['entities'][ucfirst($e)]['sitelinks']['svwiki']['url'];
                                else
                                    $eArray[$e] = $response['entities'][ucfirst($e)]['sitelinks']['svwiki']['title'];
                            }
                            return $eArray;
                        }
                    }
                }
            }
        }
        #Given an article this returns the intro of this article. Also removes any cooridinates tag
        function getArticleIntro($article) {
            if ($article) {
                $maxChar = 250; #Could for some reason not set this through param in function call
                $apiurl = 'http://sv.wikipedia.org/w/api.php?';
                $query = Array( 'action'=>'query',
                                'prop'=>'extracts',
                                'format'=>'php',
                                'exchars'=>$maxChar,
                                'exintro'=>'',
                                'explaintext'=>'',
                                'titles'=>$article
                               );
                $queryUrl = $apiurl.http_build_query($query, $enc_type='PHP_QUERY_RFC3986');
                #$queryUrl = $apiurl.'action=query&prop=extracts&format=php&exchars='.$maxChar.'&exintro=&titles='.rawurlencode($article);
                $page = ApiBase::get_curl_data($queryUrl);
                if ( is_null($page) )
                    return null;
                else{
                    $response = unserialize($page);
                    $pageId = key($response['query']['pages']);
                    if($pageId!=-1){
                        $intro = $response['query']['pages'][$pageId]['extract'];
                        #remove any coordinates templates
                        $pos = strpos($intro, "Koordinater:");
                        if ($pos !== false){
                            $newintro = trim(substr($intro, 0, $pos));
                            $endpos = strpos($intro, "\n", $pos+1);
                            if ($endpos !== false)
                                $newintro .= ' '.trim(substr($intro, $endpos));
                            $intro=$newintro;
                        }
                        return $intro;
                    }
                }
            }
        }
        #string comparison
        function startsWith($haystack, $needle){
            return !strncmp($haystack, $needle, strlen($needle));
        }
    }
    
    class CharacterLimitException extends Exception { } //max 512 characters in a parameter or else $_GET fails (external limit)
    class ValueLimitException extends Exception { } //max 50 values in a parameter
?>
