<?php
    /*
     * Creates a GeoJSON file of the desired output
     * Might be better to build this so that descriptions are only added on request (to avoid unncessary api calls)
     */
    class FormatGeojson{
        private function initialise(){
            /* Setting header */
            @header ("content-type: text/json charset=utf-8");
        }
        
        private function finalise($features, $head){
            /*Final wrapping*/
            $geo = Array(
                         'type' => 'FeatureCollection',
                         'features' => $features,
                         'head' => $head
                         );
            return ($geo);
        }
        
        private function writeRow($row){
            $row = $row['hit'];
            #Ignore rows without coords
            if (!empty($row['lat']) and !empty($row['lon'])){
                $feature = Array(
                                 'type' => 'Feature',
                                 'id' => $row['id'],
                                 'geometry' => Array(
                                                     'type' => 'Point',
                                                     'coordinates' => Array((float)$row['lon'], (float)$row['lat'])
                                                     )
                                 );
                $handled = Array('id','lat','lon');
                
                $prop=Array();
                foreach($row as $key => $value){
                    if (in_array($key, $handled)){
                        continue;
                    }elseif ($key == 'county'){
                        $prop[$key] = 'SE-'.$value;
                    }elseif ($key == 'wiki_article'){
                        $prop['wiki'] = $value;
                    }else {
                        $prop[$key] = $value;
                    }
                }
                
                $feature['properties'] = $prop;
                
                #thumb using ApiBase::getImageFromCommons($row['image'],$imgsize)
                #artists using:
                ## $artist = Array()
                ## $artist_info = ApiBase::getArtistInfo($row['id']);
                ## if (!empty($artist_info)){
                ##    foreach ($artist_info as $ai){
                ##          array_push($artist, Array('wiki' => $ai['wiki'], 'name' => $ai['name']));
                ##    }
                ## }else {
                ##    $artists = explode(';',$row['artist']);
                ##    foreach ($artists as $a){
                ##          array_push($artist, Array('name' => $a));
                ##    }
                ## }
                ##
                
                return($feature);
            }
        }
        
        function output($results){
            if($results['head']['status'] == '0') #Fall back to xml if errors
                Format::outputXml($results);
            else{
                self::initialise();
                #Output each row in the body
                $features=Array();
                foreach($results['body'] as $row){
                    $f = self::writeRow($row);
                    if ($f) {
                        array_push($features, $f);
                    }
                }
                #finalise
                $geojson = self::finalise($features, $results['head']);
                #print as json
                echo json_encode($geojson);
            }
        }
    }
?>
