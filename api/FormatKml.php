<?php
    /*
     * Creates a KML file of the desired output
     * Might be better to build this so that descriptions are only added on request (to avoid unncessary api calls)
     */
    class FormatKml{
        private function initialise(){
            /* Setting XML header */
            @header ("content-type: text/xml charset=UTF-8");
            /* Initializing the XML Object */           
            $xml = new XmlWriter();
            $xml->openMemory();
            $xml->setIndent(true);
            $xml->setIndentString('    ');
            $xml->startDocument('1.0', 'UTF-8');
            return ($xml);
        }
        
        private function setProperties(XMLWriter $xml){
            $xml->startElement('kml');
            $xml->writeAttribute('xmlns','http://www.opengis.net/kml/2.2');
            
            #Setting document properties
            $xml->startElement('Document');
                $xml->startElement('Style');
                $xml->writeAttribute('id','monumentStyle');
                    $xml->startElement('IconStyle');
                    $xml->writeAttribute('id','monumentIcon');
                        $xml->startElement('Icon');
                            $xml->startElement('href');
                                $xml->text('http://maps.google.com/mapfiles/kml/paddle/ylw-blank.png');
                            $xml->endElement();
                        $xml->endElement();
                        $xml->startElement('hotSpot');
                            $xml->writeAttribute('x','0.5');
                            $xml->writeAttribute('y','0');
                            $xml->writeAttribute('xunits','fraction');
                            $xml->writeAttribute('yunits','fraction');
                        $xml->endElement();
                    $xml->endElement();
                $xml->endElement();
                $xml->startElement('Style');
                $xml->writeAttribute('id','monPicStyle');
                    $xml->startElement('IconStyle');
                    $xml->writeAttribute('id','monPicIcon');
                        $xml->startElement('Icon');
                            $xml->startElement('href');
                                $xml->text('http://maps.google.com/mapfiles/kml/paddle/blu-circle.png');
                            $xml->endElement();
                        $xml->endElement();
                        $xml->startElement('hotSpot');
                            $xml->writeAttribute('x','0.5');
                            $xml->writeAttribute('y','0');
                            $xml->writeAttribute('xunits','fraction');
                            $xml->writeAttribute('yunits','fraction');
                        $xml->endElement();
                    $xml->endElement();
                $xml->endElement();
        }
        
        private function finalise(XMLWriter $xml){
            /* Closing last XML nodes */
            $xml->endElement(); #end Document
            $xml->endElement(); #end kml
        }
        
        private function writeRow(XMLWriter $xml, $row, $muni_names){
            $row = $row['hit'];
            #Ignore rows without coords
            if (!empty($row['lat']) and !empty($row['lon'])){
                $xml->startElement('Placemark');
                $placemarkId = $row['id'];
                $xml->writeAttribute('id',htmlspecialchars( $placemarkId ));
                    if (!empty($row['title'])){
                        $xml->startElement('title');
                            $xml->text(htmlspecialchars( $row['title'] ));
                        $xml->endElement();
                    }
                    $xml->startElement('description');
                        $desc = '';
                        if (!empty($row['image'])){
                            $imgsize = 100;
                            $desc .= '<a href="http://commons.wikimedia.org/wiki/File:' . rawurlencode($row['image']) . '" target="_blank">';
                            $desc .= '<img src="' . ApiBase::getImageFromCommons($row['image'],$imgsize) . '" align="right" />';
                            $desc .= '</a>';
                            $styleUrl = '#monPicStyle';
                        }else
                            $styleUrl = '#monumentStyle';
                        $desc .= '<ul>';
                        if (!empty($row['title'])){
                            $desc .= '<li> '; #title
                            $desc .= '<b>'.htmlspecialchars($row['title']).'</b>';
                            $desc .= '</li>';
                        }
                        $desc .= '<li> '; #artist - year
                        $artist_info = ApiBase::getArtistInfo($row['id']);
                        if (!empty($artist_info)){
                            foreach ($artist_info as $ai){
                                if($ai['wiki']){
                                    #$desc .= '<a href="https://wikidata.org/wiki/' . rawurlencode($ai['wiki']) . '">';
                                    $desc .= '<a href="'.ApiBase::getArticleFromWikidata($ai['wiki']).'" target="_blank">';
                                    $desc .= ''.htmlspecialchars($ai['name']);
                                    $desc .= '</a>';
                                } else
                                    $desc .= ''.htmlspecialchars($ai['name']);
                                $desc .= ', ';
                            }
                            $desc = substr($desc, 0, -2); #remove trailing ","
                            if (!empty($row['year']))
                                $desc .= ' - '.htmlspecialchars($row['year']);
                        }
                        elseif (!empty($row['artist'])){
                            $desc .= htmlspecialchars($row['artist']);
                            if (!empty($row['year']))
                                $desc .= ' - '.htmlspecialchars($row['year']);
                        }elseif (!empty($row['year']))
                            $desc .= htmlspecialchars($row['year']);
                        $desc .= '</li><li> '; #Muni - address
                        $desc .= htmlspecialchars($muni_names[$row['muni']]);
                        if (!empty($row['district']))
                            $desc .= ' ('.htmlspecialchars($row['district']).')';
                        if (!empty($row['address']))
                            $desc .= ' - '.htmlspecialchars($row['address']);
                        #Description
                        if (!empty($row['wiki_article'])){
                            #get descrition from wikipage
                            $desc .= '</li><br/><li>'.ApiBase::getArticleIntro(ApiBase::getArticleFromWikidata($row['wiki_article'], $getUrl=false));
                            $desc .= '</li><br/><li>'.htmlspecialchars('Läs mer om ');
                            $desc .= '<a href="'.ApiBase::getArticleFromWikidata($row['wiki_article']).'" target="_blank">';
                            $desc .= htmlspecialchars('konstverket på Wikipedia');
                            $desc .= '</a>.';
                        }
                        else if (!empty($row['descr']))
                            $desc .= '</li><br/><li>'.htmlspecialchars($row['descr']);
                        $desc .= '</li></ul>';
                        $xml->writeCData($desc);
                    $xml->endElement();
                    $xml->startElement('styleUrl');
                        $xml->text($styleUrl);
                    $xml->endElement();
                    $xml->startElement('Point');
                        $xml->startElement('coordinates');
                            $xml->text($row['lon'].','.$row['lat']);
                        $xml->endElement();
                    $xml->endElement();
                $xml->endElement();
            }
        }
        
        function outputWarning(XMLWriter $xml, $head){
            $text = $head['hits'];
            if (!empty($head['warning']))
                $text .="\nWarning: ".$head['warning'];
            if (!empty($text))
                $xml->writeComment($text);
        }
        
        function output($results){
            if($results['head']['status'] == '0') #Fall back to xml if errors
                Format::outputXml($results);
            else{
                $xml = self::initialise();
                self::outputWarning($xml, $results['head']);
                self::setProperties($xml);
                #Output each row in the body
                $muni_names = ApiBase::getMuniNames();
                foreach($results['body'] as $row)
                    self::writeRow($xml, $row, $muni_names);
                    
                #finalise
                self::finalise($xml);
                #print
                echo $xml->outputMemory(true);
            }
        }
    }
?>
