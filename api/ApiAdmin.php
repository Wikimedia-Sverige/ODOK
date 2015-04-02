<?php
    /*
     * Some functions that will not be of interest to the average user
     *
     *   *diff: produces a list of changes in main_table wrt. audit
     *   *objectlessArtist: produces a list of artists that have no objects
     *   *yearlessArtist: produces a list of artists that have no death_year
     *                    and where birth_year is also missing or occured more
     *                    than 100years ago where
     *   *artistlessObject: produces a list of objects that have no linked artists
     *   *info: Displays all known info for a given object as identified by it's id and table
     */

    class ApiAdmin{
        #assist function for getChanges
        private function colAsmPrefix($col){
            return $col.'` AS m_'.$col;
        }
        private function colAsaPrefix($col){
            return $col.'` AS a_'.$col;
        }

        /*
         * Goes through all entries (for the current constraint) with ugc=1
         * and returns a list of the changes that have been made wrt.
         * the original (audit).
         */
        private function getChanges($limit, $offset, $constraints){
            #list of columns available in the audit_table
            $cols = Array('id', 'title', 'artist', 'descr', 'year', 'year_cmt', 'type', 'material', 'inside', 'address', 'county', 'muni', 'district', 'lat', 'lon', 'source', 'official_url', 'owner', 'cmt', 'created');
            #prepare sql statement
            $mainCols = '`main_table`.`'.implode(', `main_table`.`', array_map('self::colAsmPrefix', $cols));
            $auditCols = '`audit_table`.`'.implode(', `audit_table`.`', array_map('self::colAsaPrefix', $cols));

            $query = '
                SELECT SQL_CALC_FOUND_ROWS '.$mainCols.', '.$auditCols.'
                FROM `main_table`, `audit_table`
                WHERE `main_table`.`ugc` = 1
                AND `main_table`.`id` = `audit_table`.`id`
                ';
            $query = isset($constraints) ? ApiBase::addConstraints($query.'AND `main_table`.', $constraints, '`main_table`.') : $query;
            $query .= 'LIMIT '.mysql_real_escape_string($offset).', '.mysql_real_escape_string($limit).'
                ';
            #run query
            $error=false;
            try{
                $response = ApiBase::doQuery($query);
                $hits = ApiBase::doQuery('SELECT FOUND_ROWS()');
            }catch (Exception $e){
                throw $e;
                $error=true;
            }
            if(!$error){
                #go through each row of response and compare audit to main
                $body = Array();
                foreach ($response as $r){
                    $r = ApiBase::sanitizeBit1diff($r);
                    $diff = Array();
                    $diff['id'] = $r['m_id'];
                    foreach ($cols as $c){
                        if ($r['m_'.$c] != $r['a_'.$c])
                            $diff[$c] = Array('new' => $r['m_'.$c], 'old' => $r['a_'.$c]);
                    }
                    if (count($diff)>1) #so as to remove any entries with only an id (i.e. only image added)
                        $body[] = Array('diff' => $diff);
                }
                return Array($body, $hits);
            }
        }

        #displays all known info about a given object
        private function getInfo($table, $id){
            $query = '
                SELECT *
                FROM `'.mysql_real_escape_string($table).'_table`
                WHERE id = "'.mysql_real_escape_string($id).'"
                ';
            #run query
            try{
                $response = ApiBase::doQuery($query);
            }catch (Exception $e){throw $e;}
            return ApiBase::sanitizeBit1($response[0]);
        }

        #returns a list of artists withouth any linked objects
        private function getArtistlessObject($limit, $offset){
            $query = '
                SELECT SQL_CALC_FOUND_ROWS id, title, artist
                FROM `main_table`
                WHERE id NOT IN
                   (SELECT object FROM `artist_links`)
                ';
            #run query
            try{
                $response = ApiBase::doQuery($query);
                $hits = ApiBase::doQuery('SELECT FOUND_ROWS()');
            }catch (Exception $e){throw $e;}
            foreach ($response as $r)
                $body[] = Array('hit' => $r);
            return Array($body, $hits);
        }

        #returns a list of objects without any artists
        private function getObjectlessArtist($limit, $offset){
            $query = '
                SELECT SQL_CALC_FOUND_ROWS id, CONCAT_WS(" ", first_name, last_name) AS name
                FROM `artist_table`
                WHERE id NOT IN
                   (SELECT artist FROM `artist_links`)
                ';
            #run query
            try{
                $response = ApiBase::doQuery($query);
                $hits = ApiBase::doQuery('SELECT FOUND_ROWS()');
            }catch (Exception $e){throw $e;}
            foreach ($response as $r)
                $body[] = Array('hit' => $r);
            return Array($body, $hits);
        }

        #returns a list of artists (name and id) without any linked objects
        #convert date to year for comparisson
        private function getYearlessArtist($limit, $offset){
            $query = '
                SELECT SQL_CALC_FOUND_ROWS id, CONCAT_WS(" ", first_name, last_name) AS name, `birth_year`, `death_year`
                FROM `artist_table`
                WHERE `death_year` IS NULL
                AND (
                        `birth_year` IS NULL
                     OR (
                            `birth_year` IS NOT NULL
                        AND birth_year+ 100 < YEAR(CURRENT_TIMESTAMP)
                        )
                    )
                ';
            #run query
            try{
                $response = ApiBase::doQuery($query);
                $hits = ApiBase::doQuery('SELECT FOUND_ROWS()');
            }catch (Exception $e){throw $e;}
            foreach ($response as $r)
                $body[] = Array('hit' => $r);
            return Array($body, $hits);
        }

        function run($constraints){
            #set limit
            list ($limit, $w) = ApiBase::setLimit($_GET['limit']);
            $warning = isset($w) ? $w : null;
            #set offset
            list ($offset, $w) = ApiBase::setOffset($_GET['offset']);
            $warning .= isset($w) ? $w : '';

            try{
                switch (strtolower($_GET['function'])) {
                    case 'diff':
                        list ($response, $hits) = self::getChanges($limit, $offset, $constraints);
                        break;
                    case strtolower('objectlessArtist'):
                        #list of artists that have no objects
                        list ($response, $hits) = self::getObjectlessArtist($limit, $offset);
                        break;
                    case strtolower('yearlessArtist'):
                        list ($response, $hits) = self::getYearlessArtist($limit, $offset);
                        break;
                    case strtolower('artistlessObject'):
                        list ($response, $hits) = self::getArtistlessObject($limit, $offset);
                        break;
                    case 'info':
                        #e.g. funtion=info&table=source&id=4
                        #Displays all known info for a given id of a given table
                        $table = $_GET['table'];
                        $id = $_GET['id'];
                        if (isset($table) and isset($id))
                            $response = self::getInfo($table, $id);
                        else{
                            return ApiBase::makeErrorResult(
                            '631',
                            'Admin Failed. '.
                                'Function "info" must be used together with a "table" and "id" parameter.',
                            $warning
                            );
                        }
                        break;
                    default:
                        return ApiBase::makeErrorResult(
                            '632',
                            'Admin Failed. '.
                                'Sorry but ['.$_GET['function'].'] is not a valid function for the "admin" action.',
                            $warning
                            );
                        break;
                }
            }catch (Exception $e) {
                return ApiBase::makeErrorResult(
                '630',
                'Admin Failed. '.
                    'Probably error in one of the constraints. ['.$e->getMessage().']',
                $warning
                );
            }
            $head = Array();
            if (isset($hits)){
                $hits = $hits[0]['FOUND_ROWS()'];
                $head['hits'] = $offset.'–'.($offset+count($response)).' of '.$hits;
                $head['limit'] = $limit;
                if($hits > $offset+$limit)
                    $head['continue'] = $offset+$limit;
            }
            if(!empty($warning))
                $head['warning'] = $warning;
            return ApiBase::makeSuccessResultHead($head,$response);
        }
    }
?>
