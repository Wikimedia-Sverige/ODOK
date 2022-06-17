<?php
    /*
     * Gives information about the artists in the database.
     * Desired functions:
     * 1. get artist info (including array of all artwork ids) by:
     *  a. artistId
     *  b. wikidataId (of artist)
     *  c. by name (return array of artists matching) - need to sort out first/last name
     *  d. by artwork id (return array of artists matching)
     *  e. birth/death year (span)
     * Also should reuse the following parameters:
     *    limit: max number of results (artists) returned (must be in range 1-500, defaults to 10)
     *    offset: which result to start showing (used in combination with limit)
     *    show: the parameters to show (possibly skip this)
     */

    class ApiArtist{

        # set which parameters to include in output
        private static function setSelect($show, $prefix = NULL){
            $getWorks = true; # default behaviour
            if (isset($prefix)){
                $prefix = $prefix.'.';
            } else {
                $prefix = '';
            }

            # 'works' is dealt with separately
            $allowed = Array('id', 'first_name', 'last_name', 'wiki',
                             'changed', 'birth_date', 'death_date',
                             'birth_year', 'death_year', 'creator');
            $warning = '';
            if(isset($show)){
                $shows = explode('|', $show);

                # handle works
                $i = array_search('works', $shows);
                if ($i){
                    # remove from list and renumber entries
                    array_splice($shows, $i, 1);
                    $getWorks = true;
                } else {
                    $getWorks = false;
                }

                # handle rest
                $i=0;
                foreach($shows as $s){
                    if (!in_array($s, $allowed)){
                        $warning = $warning.'The parameter "'.$s.'" does not exist and was therefore disregarded. ';
                        unset($shows[$i]);
                    }
                    $i++;
                }
                $select = $prefix.'`'.implode('`, '.$prefix.'`', array_map([ApiBase::getMysql(), 'real_escape_string'], $shows)).'`';
                return Array($select, $getWorks, $warning);
            }else{
                $select = $prefix.'`'.implode('`, '.$prefix.'`', array_map([ApiBase::getMysql(), 'real_escape_string'], $allowed)).'`';
                return Array($select, $getWorks, $warning);
            }
        }

        #given a list of artists this returns all of their associated works
        private static function getWorks($artist, $warning){
            # set group_concat_max_len explicitly so that we are always testing agains the same limit
            ApiBase::doQuery('SET SESSION group_concat_max_len = '.ApiBase::group_concat_max_len);
            $query = '
                SELECT al.`artist` as artist, GROUP_CONCAT(al.`object` SEPARATOR "|") AS objects
                FROM `artist_links` al
                INNER JOIN `artist_table` at ON at.`id` = al.`artist`
                WHERE at.`id` in (
                "'.implode('", "',array_map([ApiBase::getMysql(), 'real_escape_string'], $artist)).'"
                )
                GROUP BY artist;';

            #do query
            try{
                $response = ApiBase::doQuery($query);
            }catch (Exception $e) {
                return ApiBase::makeErrorResult(
                '610',
                'Select Failed. '.
                            'Probably wrong name supplied.['.$e->getMessage().']',
                $warning
                );
            }

            $w = '';
            #check that results were not truncated, since this is a silent fail
            try{
                ApiBase::groupConcatTest($response, 'objects', 'works');
            }catch (CharacterLimitException $e) {
                $w = $e->getMessage();
            }

            # put together new array of works
            $works = Array();
            foreach ($response as $r)
                $works[$r['artist']] = explode('|', $r['objects']);

            return Array($works, $w);

        }


        # constraints comes from ApiBase::readConstraints
        # and identifies id, wiki and year
        static function run($constraints){
            #either look up on artwork_id or one of the others
            $prefix = null;
            $w = null;
            $otherSelectors = Array(
                'wiki', 'id', 'first_name', 'last_name', 'name',
                'birth_year', 'death_year', 'is_dead', 'lifespan');
            if (isset($_GET['artwork'])){
                $prefix = 'at';
                if (count(array_intersect($otherSelectors, array_keys($_GET))) > 0){  # if any of $otherSelectors were provided
                    $w = 'The artwork parameter cannot be combined with any other selectors, these are therefore disregarded. ';
                }
            }
            $warning = isset($w) ? $w : null;
            #set limit
            list ($limit, $w) = ApiBase::setLimit(key_exists('limit', $_GET) ? $_GET['limit'] : null);
            $warning = isset($w) ? $warning.$w : $warning;
            #set offset
            list ($offset, $w) = ApiBase::setOffset(key_exists('offset', $_GET) ? $_GET['offset'] : null);
            $warning = isset($w) ? $warning.$w : $warning;
            #load list of parameters to select
            list ($select, $getWorks, $w) = self::setSelect(key_exists('show', $_GET) ? $_GET['show'] : null, $prefix);
            $warning = isset($w) ? $warning.$w : $warning;

            #Needs support for
            # name, first_name, last_name as well (with name=Concatenate(first, ' ', last))
            # as a constraint

            # Look up on artwork_id or other
            $query = null;
            if (isset($_GET['artwork'])){
                $query = '
                SELECT SQL_CALC_FOUND_ROWS '.$select.'
                FROM `artist_table` at
                INNER JOIN `artist_links` al ON al.`artist` = at.`id`
                WHERE al.`object` in (
                "'.implode('", "',array_map([ApiBase::getMysql(), 'real_escape_string'], explode('|', $_GET['artwork']))).'"
                )
                ';
            }
            else{
                #add available constraints
                $query = '
                SELECT SQL_CALC_FOUND_ROWS '.$select.'
                FROM `artist_table`
                ';
                $query = isset($constraints) ? ApiBase::addConstraints($query.'WHERE ', $constraints) : $query;
            }
            # add limit
            $query .= 'LIMIT '.ApiBase::getMysql()->real_escape_string($offset).', '.ApiBase::getMysql()->real_escape_string($limit).'
                ';
            #run query
            try{
                $response = ApiBase::doQuery($query);
                $hits = ApiBase::doQuery('SELECT FOUND_ROWS()');
                // error_log("hits = $hits");
            }catch (Exception $e) {
                return ApiBase::makeErrorResult(
                '610',
                'Select Failed. '.
                            'Probably wrong name supplied.['.$e->getMessage().']',
                $warning
                );
            }

            # look up works for each artist
            $works = null;
            if ($getWorks and $response) {
                $artists = Array();
                foreach ($response as $r) {
                    if(key_exists('id', $r)) {
                        array_push($artists, $r['id']);
                    }
                }
                list ($works, $w) = self::getWorks($artists, $warning);
                $warning = isset($w) ? $warning.$w : $warning;
            }

            #collect results
            $body = Array();
            if($response) {
                foreach ($response as $r) {
                    if ($getWorks) {
                        $r['works'] = Array();
                        if (key_exists('id', $r) and isset($works[$r['id']])){
                            foreach ($works[$r['id']] as $work) {
                                array_push($r['works'], Array('work' => $work)); # so that xml plays nice
                            }
                        }
                    }
                    array_push($body, Array('hit' => ApiBase::sanitizeBit1($r))); # so that xml plays nice
                }
            }
            #Did we get all?
            $hits = $hits[0]['FOUND_ROWS()'];
            $head = Array(
                'hits' => $offset.'–'.($offset+count($body)).' of '.$hits,
                'limit' => $limit
            );
            if($hits > $offset+$limit)
                $head['continue'] = $offset+$limit;
            if(!empty($warning))
                $head['warning'] = $warning;
            $results = ApiBase::makeSuccessResultHead($head,$body);
            return $results;
        }
    }
?>
