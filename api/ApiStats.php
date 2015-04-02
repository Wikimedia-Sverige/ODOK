<?php
    /*
     * Gives statistics about the database.
     * In addition to the ordinary constraints this module listens for the
     * following parameters:
     *   table: specifies which table (without _table) to look at.
     *          "all" shows all
     *   column: (pipe-separated) columns which must not be empty.
     *          "coords" tests both lat and lon at the same time.
     *   split: ('muni' or 'county') showes the result broken down by
     *          municipality or county
     *
     * constraints may also be specified. current allowed ones are:
     *  muni, county
     *
     * TO DO:
     * add more constraints
     * give names for muni and county - these last two could be done centrally
     * shift constraints to main api.php
     */
    class ApiStats{
        #individual stats modules

        #TABLE: this will give you the number of entries in a given table.
        private function countTable($target, $constraints){
            $allowedTables = Array('main', 'artist', 'audit', 'county', 'muni', 'source', 'ugc', 'aka');
            if ($target == 'all')
                $tables = $allowedTables;
            else
                $tables = explode('|', $target);
            foreach($tables as $t){
                try{
                    $tmp = self::countSingleTable($t, $constraints);
                    $rows[$t] = $tmp[$t];
                }
                catch (Exception $e) {
                    throw $e;
                    break;
                }
            }
            return $rows;
        }

        private function countSingleTable($target, $constraints){
            $query = '
                    SELECT COUNT(*) AS `'.mysql_real_escape_string($target).'`
                    FROM `'.mysql_real_escape_string($target).'_table`
                ';
            if (($target == 'main') or ($target == 'audit'))
                $query = isset($constraints) ? ApiBase::addConstraints($query.'Where ', $constraints) : $query;
            try{
                $response = ApiBase::doQuery($query);
            }catch (Exception $e) {throw $e;}
            return $response[0];
        }

        #COLUMN: Shows the number of items in the main table where the given column is non-zero
        private function countColumn($column, $constraints){
            $allowedcols = Array('id', 'title', 'artist', 'descr', 'year', 'year_cmt', 'type', 'material', 'inside', 'address', 'county', 'muni', 'district', 'lat', 'lon', 'removed', 'image', 'source', 'ugc', 'changed', 'created', 'wiki', 'list', 'commons_cat', 'official_url', 'same_as', 'free', 'cmt', 'owner'); #etc.
            if ($column == 'all')
                $cols = $allowedcols;
            else
                $cols = explode('|', $column);
            $rows = Array();
            foreach($cols as $c){
                try{
                    $tmp = self::countSingleColumn($c, $constraints);
                    $rows[$c] = $tmp[$c];
                }
                catch (Exception $e) {
                    throw $e;
                    break;
                }
            }
            return $rows;
        }

        private function countSingleColumn($column, $constraints){
            $query = '
                SELECT COUNT(*) AS `'.mysql_real_escape_string($column).'`
                FROM `main_table`
                WHERE ';
            $query = ApiBase::notEmpty($query, $column);
            $query = isset($constraints) ? ApiBase::addConstraints($query.'AND ', $constraints) : $query;
            #peform query and output
            try{
                $response = ApiBase::doQuery($query);
            }catch (Exception $e) {throw $e;}
            return $response[0];
        }

        #SPLIT: Showes the result broken down by municipality, county or source
        private function splitSelector($split, $table, $column, $constraints, $warning){
            if (isset($split)){
                $splitable = Array('main', 'audit');
                if (count(explode('|', $table))>1 or count(explode('|', $column))>1)
                    $warning .= 'Cannot use split-parameter with multiple tables/columns; ignoring split parameter. ';
                elseif (!in_array($table, $splitable))
                    $warning .= 'Cannot use split-parameter with table='.$table.'; ignoring split parameter. ';
                else{
                    switch ($split){
                        case 'muni':
                            $response = self::splitBy('muni', $table, $column, $constraints);
                            break;
                        case 'county':
                            $response = self::splitBy('county', $table, $column, $constraints);
                            break;
                        case 'source':
                            $response = self::splitBy('source', $table, $column, $constraints);
                            break;
                        default:
                            $warning .= 'Invalid split-parameter; ignoring it. ';
                            break;
                    }
                }
            }
            if (!isset($response)){ #perform default action
                $response = isset($column) ? self::countColumn($column, $constraints) : self::countTable($table, $constraints);
            }
            return Array($response, $warning);
        }

        private function splitBy($sp_table, $table, $column, $constraints){
            $num_label_sql = isset($column) ? mysql_real_escape_string($column) : $table;
            $sp_table_sql = mysql_real_escape_string($sp_table).'_table';
            $label_sql = mysql_real_escape_string($sp_table).'_name';
            $real_table_sql = mysql_real_escape_string($table).'_table';
            $query = '
                SELECT `'.$sp_table_sql.'`.`name` AS `'.$label_sql.'`, COUNT(*) AS `'.$num_label_sql.'`
                FROM `'.$real_table_sql.'`, `'.$sp_table_sql.'`
                WHERE `'.$real_table_sql.'`.`'.mysql_real_escape_string($sp_table).'` = `'.$sp_table_sql.'`.`id`
                ';
            $query = isset($column) ? ApiBase::notEmpty($query.'AND ', $column) : $query;
            $query = isset($constraints) ? ApiBase::addConstraints($query.'AND ', $constraints) : $query;
            $query .= 'GROUP BY `'.$label_sql.'`
                ORDER BY `'.$label_sql.'` ASC
                ';
            try{
                $response = ApiBase::doQuery($query);
            }catch (Exception $e) {throw $e;}
            foreach ($response as $r){
                $mod_resp[] = Array($sp_table => $r);
            }
            return $mod_resp;
        }

        #Loads the parameters and decides which statistics funtion to run
        function run($constraints){
            /*
             * use options to choose a query generating function
             * then
             */
            $table = isset($_GET['table']) ? strtolower($_GET['table']) : null;
            $column = isset($_GET['column']) ? strtolower($_GET['column']) : null;
            $split = isset($_GET['split']) ? strtolower($_GET['split']) : null;

            #choose function based on given parameters
            try{
                if (isset($table) and isset($column)){
                    $warning = 'You cannot specify both table and column; ignoring table parameter. ';
                    list($response, $warning) = self::splitSelector($split, 'main', $column, $constraints, $warning);
                }elseif (isset($table)){
                    list($response, $warning) = self::splitSelector($split, $table, NULL, $constraints, $warning);
                }elseif (isset($column)){
                    list($response, $warning) = self::splitSelector($split, 'main', $column, $constraints, $warning);
                }elseif (isset($split)){ #only split is set
                    $warning = 'No table specified for split; assuming table = "main". ';
                    list($response, $warning) = self::splitSelector($split, 'main', NULL, $constraints, $warning);
                }else{
                    $warning = 'Neither column, table nor split parameter defined; assuming table = "all". ';
                    $response = self::countTable('all', $constraints);
                }
            }catch (Exception $e) {
                return ApiBase::makeErrorResult(
                '620',
                'Count Failed. '.
                    'Probably wrong parameter name supplied. ['.$e->getMessage().']',
                $warning
                );
            }
            return ApiBase::makeSuccessResult($warning,$response);

        }
    }
?>
