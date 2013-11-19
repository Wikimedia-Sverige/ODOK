<?php
    /*
     * Creates a GeoJSON file of the desired output
     * KNOWN BUGS:
     *   If some but not all artists have artist_table entries then only these are included
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
        
        private function writeRowFull($row, $imgsize = 100){
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
                array_push($handled, 'inside','address','county','muni','district');
                $spatial = Array(
                                 'inside' => $row['inside'],
                                 'address' => $row['address'],
                                 'county' => 'SE-'. $row['county'],
                                 'muni' =>  $row['muni'],
                                 'district' => $row['district']
                                 );
                $prop['spatial'] = $spatial;
                
                #image
                array_push($handled, 'image');
                if ($row['image']) {
                    $prop['image'] = Array(
                            'filename' => $row['image'],
                            'thumb' => ApiBase::getImageFromCommons($row['image'],$imgsize)
                            );
                }else {
                    $prop['image'] = null;
                }
                
                #descriptions
                array_push($handled, 'descr', 'wiki_article', 'official_url');
                $desc_text = Array(
                                 'descr' => $row['descr'],
                                 'wiki' => ApiBase::getArticleFromWikidata($row['wiki_article']),
                                 'wikidata' => !empty($row['wiki_article']) ? $row['wiki_article'] : null,
                                 'official' => !empty($row['official_url']) ? $row['official_url'] : null,
                                 'ingress' => !empty($row['wiki_article']) ? ApiBase::getArticleIntro(ApiBase::getArticleFromWikidata($row['wiki_article'], $getUrl=false)) : null,
                                 );
                $prop['descriptions'] = $desc_text;
                
                #artists
                array_push($handled, 'artist');
                $artist = Array();
                $artist_info = ApiBase::getArtistInfo($row['id']);
                if (!empty($artist_info)){
                   foreach ($artist_info as $ai){
                         array_push($artist, Array(
                                                   'wiki' => ApiBase::getArticleFromWikidata($ai['wiki']),
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
                    }else {
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
                    }elseif ($key == 'wiki_article'){
                        $prop['wiki'] = $value;
                    }else {
                        $prop[$key] = $value;
                    }
                }
                
                $feature['properties'] = $prop;       
                return($feature);
            }
        }
        
        function output($results, $full=False){
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
                echo json_encode($geojson);
            }
        }
    }
?>
