<?php
    /*
     * Performs a standard SQL query on the database.
     * In addition to the ordinary constraints this module listens for the
     * following parameters:
     *    limit: max number of results returned (must be in range 1-500, defaults to 10)
     *    offset: which result to start showing (used in combination with limit)
     *    view: the view used [strict, enhanced, normal].
     *    show: the parameters to show
     *
     * To do:
     *    Numerical constraints e.g. year > X, coords inside box
     */

    require_once('ApiMain.php');

    class ApiGet{
        /* Swith between different views. Defaults to "normal" */
        static function setView($view){
            /* Swith between different views */
            $warning = '';
            if(isset($view)){
                $view = strtolower($view);
                switch ($view) {
                    case 'strict':
                        $target_table = "official_strict_view";
                        break;
                    case 'enhanced':
                        $target_table = "official_enhanced_view";
                        break;
                    case 'normal':
                        $target_table = "main_table";
                        break;
                    default:
                        $warning = 'Sorry but "'.$view.'" is not a valid view; showing "normal" view. ';
                        $target_table = "main_table";
                };
            } else {
                $target_table = "main_table";
            }
            return Array($target_table, $warning);
        }

        private static function setSelect($show){
            $allowed = Array('id', 'title', 'artist', 'descr', 'year', 'year_cmt',
                             'type', 'material', 'inside', 'address', 'county', 'muni', 'district',
                             'lat', 'lon', 'removed', 'image', 'source', 'ugc', 'changed', 'created',
                             'wiki', 'list', 'commons_cat', 'official_url', 'same_as',
                             'free', 'cmt', 'owner');
            $warning = '';
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
                $select = '`'.implode('`, `', array_map([ApiMain::$mysqli, 'real_escape_string'], $shows)).'`';
                return Array($select, $warning);
            }else{
                $select = '`'.implode('`, `', array_map([ApiMain::$mysqli, 'real_escape_string'], $allowed)).'`';
                return Array($select, $warning);
            }
        }


        static function run($constraints){
            #set limit
            list ($limit, $w) = ApiBase::setLimit(key_exists('limit', $_GET) ? $_GET['limit'] : null);
            $warning = isset($w) ? $w : null;
            #set offset
            list ($offset, $w) = ApiBase::setOffset(key_exists('offset', $_GET) ? $_GET['offset'] : null);
            $warning = isset($w) ? $warning.$w : $warning;
            #set view
            list ($target_table, $w) = self::setView(key_exists('view', $_GET) ? $_GET['view'] : null);
            $warning = isset($w) ? $warning.$w : $warning;
            #load list of parameters to select
            list ($select, $w) = self::setSelect(key_exists('show', $_GET) ? $_GET['show'] : null);
            $warning = isset($w) ? $warning.$w : $warning;
            #load constraints
            #isset($_GET['muni']) ? $constraints['muni'] = $_GET['muni'] : null;
            #isset($_GET['county']) ? $constraints['county'] = $_GET['county'] : null;

            #construct query
            $query = '
                SELECT SQL_CALC_FOUND_ROWS '.$select.'
                FROM `'.ApiMain::$mysqli->real_escape_string($target_table).'`
                ';
            $query = $constraints ? ApiBase::addConstraints($query.'WHERE ', $constraints) : $query;
            $query .= 'LIMIT '.ApiMain::$mysqli->real_escape_string($offset).', '.ApiMain::$mysqli->real_escape_string($limit).'
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
            $body = Array();
            foreach ($response as $r)
                array_push($body, Array('hit' => ApiBase::sanitizeBit1($r))); # so that xml plays nice
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
            //~ $head = Array(
                //~ 'hits' => $hits,
                //~ 'limit' => $limit,
                //~ 'warning' => $warning
                //~ );
            $results = ApiBase::makeSuccessResultHead($head,$body);
            return $results;
        }
    }
?>
