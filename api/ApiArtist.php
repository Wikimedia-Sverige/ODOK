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
     *    limit: max number of results (artists) returned (must be in range 1-100, defaults to 10)
     *    offset: which result to start showing (used in combination with limit)
     *    show: the parameters to show (possibly skip this)
     */
    class ApiArtist{

        # set which parameters to include in output
        private function setSelect($show, $prefix = NULL){
            if (isset($prefix)){
                $prefix = $prefix.'.';
            } else {
                $prefix = '';
            }
            $allowed = Array('id', 'first_name', 'last_name', 'wiki',
                             'changed', 'birth_date', 'death_date',
                             'birth_year', 'death_year', 'creator',
                             'cmt');  # 'works' would be usefull but would have to be disconnected from sql
            if(isset($show)){
                $shows = explode('|', $show);
                $i=0;
                foreach($shows as $s){
                    if (!in_array($s, $allowed)){
                        $warning = $warning.'The parameter "'.$s.'" does not exist and was therefore disregarded. ';
                        unset($shows[$i]);
                    }
                    $i++;
                }
                $select = $prefix.'`'.implode('`, '.$prefix.'`', array_map('mysql_real_escape_string', $shows)).'`';
                return Array($select, $warning);
            }else{
                $select = $prefix.'`'.implode('`, '.$prefix.'`', array_map('mysql_real_escape_string', $allowed)).'`';
                return Array($select, $warning);
            }
        }

        #given a list of artists this returns all of their associated works
        private function getWorks($artist){
            $query = '
                SELECT GROUP_CONCAT(al.`object` SEPARATOR '|') AS objects, al.`artist` as artist
                FROM `artist_links` al
                INNER JOIN `artist_table` at ON at.`id` = al.`artist`
                WHERE at.`id` in in (
                "'.implode('", "',array_map('mysql_real_escape_string', $artist)).'"
                );';

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

            $works = array();
            foreach ($response as $r)
                $works[$r['artist']] = explode('|', $r['objects']);

            return $works;

        }


        # constraints comes from ApiBase::readConstraints
        # and identifies id, wiki and year
        function run($constraints){
            $getWorks = true;  #for now
            #either look up on artwork_id or one of the others
            $prefix = null;
            $w = null;
            $other = array('wiki', 'id', 'year');
            if (isset($_GET['artwork'])){
                $prefix = 'at';
                if (in_array($other , array_keys($_GET))){
                    $w = 'The artwork parameter cannot be combined with any other selectors, these are therefore disregarded. ';
                }
            }
            $warning = isset($w) ? $w : null;
            #set limit
            list ($limit, $w) = ApiBase::setLimit($_GET['limit']);
            $warning = isset($w) ? $warning.$w : $warning;
            #set offset
            list ($offset, $w) = ApiBase::setOffset($_GET['offset']);
            $warning = isset($w) ? $warning.$w : $warning;
            #load list of parameters to select
            list ($select, $w) = self::setSelect($_GET['show'], $prefix);
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
                "'.implode('", "',array_map('mysql_real_escape_string', explode('|', $_GET['artwork']))).'"
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
            $query .= 'LIMIT '.mysql_real_escape_string($offset).', '.mysql_real_escape_string($limit).'
                ';
            #run query
            try{
                $response = ApiBase::doQuery($query);
                $hits = ApiBase::doQuery('SELECT FOUND_ROWS()');
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
            if ($getWorks) {
                $artists =array();
                foreach ($response as $r)
                    array_push($artists, $r['id']);
                $works = self::getWorks();
            }

            #collect results
            $artists =array();
            foreach ($response as $r) {
                if ($getWorks) {
                    $r['works'] = isset($works[$r['id']]) ?$works[$r['id']] : array();
                }
                $body[] = Array('hit' => ApiBase::sanitizeBit1($r));
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
