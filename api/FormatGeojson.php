<?php
    /*
     * Creates a GeoJSON file of the desired output
     * KNOWN BUGS:
     *   If some but not all artists have artist_table entries then only these are included
     */
    class FormatGeojson{
        private function initialise(){
            /* Setting headers */
            @header ("content-type: application/vnd.geo+json; charset=utf-8");
            header ("Access-Control-Allow-Origin: *");
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
        
        private function writeRowFull($row){
            # rows to skip
            $skip = Array('created', 'changed', 'ugc', 'year_cmt', 'cmt', 'owner', 'official_url');
            
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
                
                #Deal with properties
                $prop=Array();
                
                #Spatial info
                array_push($handled, 'inside','address','county','muni','district', 'removed');
                $spatial = Array(
                                 'inside' => $row['inside'],
                                 'address' => $row['address'],
                                 'county' => 'SE-'. $row['county'],
                                 'muni' =>  $row['muni'],
                                 'district' => $row['district'],
                                 'removed' => $row['removed'],
                                 );
                $prop['spatial'] = $spatial;
                
                #image
                array_push($handled, 'image');
                if ($row['image']) {
                    $prop['image'] = $row['image'];
                    # thumb is not needed as it is just
                    # "https://commons.wikimedia.org/w/thumb.php?f=" . $row['image'] . "&width=" . $size;
                    # leaving it out allows size to be set by recipient
                }else {
                    $prop['image'] = null;
                }
                
                #descriptions
                array_push($handled, 'descr', 'wiki', 'list');
                $desc_text = Array(
                                 'descr' => $row['descr'],
                                 'wikidata' => !empty($row['wiki']) ? $row['wiki'] : null,
                                 'ingress' => !empty($row['wiki']) ? ApiBase::getArticleIntro(ApiBase::getArticleFromWikidata($row['wiki'], $getUrl=false)) : null,
                                 'list' => !empty($row['list']) ? $row['list'] : null,
                                 );
                $prop['descriptions'] = $desc_text;
                
                #artists
                array_push($handled, 'artist');
                $artist = Array();
                $artist_info = ApiBase::getArtistInfo($row['id']);
                if (!empty($artist_info)){
                   foreach ($artist_info as $ai){
                         array_push($artist, Array(
                                                   'wikidata' => !empty($ai['wiki']) ? $ai['wiki'] : null,
                                                   'name' => $ai['name'])
                                                   );
                   }
                }elseif($row['artist']) {
                   $artistsList = explode(';',$row['artist']);
                   foreach ($artistsList as $a){
                         array_push($artist, Array('name' => $a));
                   }
                }else {
                    $artist = null;
                }
                $prop['artist'] = $artist;
                
                #any remaining
                foreach($row as $key => $value){
                    if (in_array($key, $handled)){
                        continue;
                    }else if (in_array($key, $skip)){
                        continue;
                    }else{
                        $prop[$key] = $value;
                    }
                }
                
                #store and return
                $feature['properties'] = $prop;
                return($feature);
            }
        }

        
        private function writeRowBasic($row){
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
                    }else {
                        $prop[$key] = $value;
                    }
                }
                
                $feature['properties'] = $prop;       
                return($feature);
            }
        }
        
        function output($results, $full=False, $compact=False){
            if($results['head']['status'] == '0') #Fall back to xml if errors
                Format::outputXml($results);
            else{
                self::initialise();
                #Output each row in the body
                $features=Array();
                foreach($results['body'] as $row){
                    if ($full){
                        $f = self::writeRowFull($row);
                    }else {
                        $f = self::writeRowBasic($row);
                    }
                    if ($f) {
                        array_push($features, $f);
                    }
                }
                #finalise
                $geojson = self::finalise($features, $results['head']);
                #print as json
                if ($compact){
                    echo json_encode($geojson);
                }else{
                    echo Format::prettyPrintJson($geojson);
                }
            }
        }
    }
?>
