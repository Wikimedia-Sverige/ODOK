<?php   
    /*
     * Outputs the query as a wikilist
     * KNOWN BUGS:
     *   If some but not all artists have artist_table entries then only these are included
     * TO DO:
     *   bettwer way of outputting all objects of a given query (i.e. continue/offset param)
     *   stick variables in head (and hide from row) based on query
     *      e.g. if query involves municipalityName=Malmö then: {{../huvud|kommun=Malmö}} and {{../rad|gömKommun=|...}} remove kommun from output
     *           if multiple things are specified (eg muni=1234|5678) then make into separate tables with this as header
     */
    
    class FormatWikilist{
        const header_template = 'Offentligkonstlista-huvud';
        const row_template = 'Offentligkonstlista';
        
        private function writeHeader(){
            /* Starting table */
            $text = "{{".self::header_template."}}\n";
            # potential of adding parameters (based on search parameters)
            return $text;
        }
        
        private function writeEnder(){
            /* Closing table and adding cateogires? */
            $text = "|}\n";
            return $text;
        }
        
        private function writeRow($row, $muni_names, $county_names){
            /* 
             * outputs a template row for the given hit
             * Ignores any entries with a "same_as" value
             */
            global $row_template;
            $row = $row['hit'];
            if (!empty($row['same_as'])){
                $text = "<!-- ".$row['id']." is a duplicate of ".$row['same_as']." -->\n";
                return $text;
            }
            $text ="{{".self::row_template;
            # potential of adding marking parameters as hidden (based on search parameters)
            $text .="\n| id           = ";
            if (!empty($row['id']))
                $text .= $row['id'];
            $text .="\n| id-länk      = ";
            if (!empty($row['official_url']))
                $text .=$row['official_url'];
            $text .="\n| titel        = ";
            if (!empty($row['title']))
                $text .=$row['title'];
            $text .="\n| artikel      = ";
            if (!empty($row['wiki_article']))
                $text .= ApiBase::getArticleFromWikidata($row['wiki_article'], $getUrl=false);
            $text .="\n| konstnär     = ";
            $artistName = self::outputArtist($row);
            if (!empty($artistName))
                $text .=$artistName;
            $text .="\n| årtal        = ";
            if (!empty($row['year']))
                $text .=$row['year'];
            $text .="\n| beskrivning  = ";
            if (!empty($row['descr']))
                $text .=$row['descr'];
            $text .="\n| typ          = ";
            if (!empty($row['type']))
                $text .=$row['type'];
            $text .="\n| material     = ";
            if (!empty($row['material']))
                $text .=$row['material'];
            $text .="\n| fri          = ";
            if (!empty($row['free'])){
                if ($row['free'] == 'unfree')
                    $text .="nej";
                else
                    $text .=$row['free'];
            }
            $text .="\n| plats        = ";
            if (!empty($row['address']))
                $text .=$row['address'];
            $text .="\n| inomhus      = ";
            if (!empty($row['inside'])){
                if($row['inside']==1)
                    $text .= "ja";
            }
            $text .="\n| län          = ";
            if (!empty($row['county']))
                $text .=$row['county'];
            $text .="\n| kommun       = ";
            if (!empty($row['muni']))
                $text .=$muni_names[$row['muni']];
            $text .="\n| stadsdel     = ";
            if (!empty($row['district']))
                $text .=$row['district'];
            $text .="\n| lat          = ";
            if (!empty($row['lat']))
                $text .=$row['lat'];
            $text .="\n| lon          = ";
            if (!empty($row['lon']))
                $text .=$row['lon'];
            $text .="\n| bild         = ";
            if (!empty($row['image']))
                $text .=$row['image'];
            $text .="\n| commonscat   = ";
            if (!empty($row['commons_cat']))
                $text .=$row['commons_cat'];
            if (!empty($row['cmt']))
                $text .="\n| fotnot       = ".$row['cmt'];
            $text .="\n}}\n";
            return $text;
        }
        
        function outputArtist($row){
            $artist_info = ApiBase::getArtistInfo($row['id']);
            $desc ='';
            $counter=2;
            if (!empty($artist_info)){
                foreach ($artist_info as $ai){
                    if($ai['wiki']){
                        $article = ApiBase::getArticleFromWikidata($ai['wiki'], $getUrl=false);
                        if ($article){ #as wikidata is no guarantee of sv.wiki article (e.g. Finnish artist)
                            $desc .= "[[".$article;
                            if ($article != $ai['name'])
                                $desc .= "|".$ai['name'];
                            $desc .= "]]";
                        } else
                            $desc .= $ai['name'];
                    } else
                        $desc .= $ai['name'];
                    if (count($artist_info) >= $counter){
                        $desc .= "\n| konstnär".$counter."    = ";
                        $counter++;
                    }
                }
                #check if any un-tabled artists were missed
                if (count($artist_info) != count(explode(';',$row['artist']))){
                    $desc .= " <!--Some unlinked artists have been missed! please add these manually from: '" .$row['artist']. "'";
                }
                return $desc; 
            }
            elseif (!empty($row['artist'])){
                $artistsList = explode(';',$row['artist']);
                foreach ($artistsList as $a){
                    $desc .= $a;
                    if (count($artistsList) >= $counter){
                        $desc .= "\n| konstnär".$counter."    = ";
                        $counter++;
                    }
                }
                return $desc; 
            }
        }
        
        function outputWarning($head){
            $text = $head['hits'];
            if (!empty($head['warning']))
                $text .="\nWarning: ".$head['warning'];
            if (!empty($text))
                $text = "<!--".$text."-->\n";
            return $text;
        }
        
        function output($results){
            if($results['head']['status'] == '0') #Fall back to xml if errors
                Format::outputXml($results);
            else{
                @header ("content-type: text/plain;charset=UTF-8");
                $muni_names = ApiBase::getMuniNames();
                $county_names = ApiBase::getCountyNames();
                $text = "";
                $text .= self::outputWarning($results['head']);
                $text .= self::writeHeader();
                foreach($results['body'] as $row)
                    $text .= self::writeRow($row, $muni_names, $county_names);
                $text .= self::writeEnder();
                
                #print
                echo $text;
            }
        }
    }
?>
