<?php
    /*
     * Set format for output array.
     * Available choices
     * json, serialized php, xml, kml, wikitable
     *
     * To do: 
     * consider moving mapping here
     */
     
    class Format{
        
        function outputJson($results){
            /* Setting up JSON headers */
            @header ("content-type: text/json charset=utf-8");
            
            $compact=False;
            if (strtolower($_GET['json']) == 'compact'){
                $compact=True;
            }
            /* Printing the JSON Object */
            if ($compact){
                echo json_encode($results);
            }else{
                echo json_encode($results, JSON_PRETTY_PRINT);
            }
        }
        
        function outputPhp($results){   
            /* Setting up PHP headers */
            header ("content-type: text/php charset=utf-8");
    
            /* Printing the PHP serialized Object*/
            echo serialize($results);
        }
                
        function outputXml($results, $xsltPath){
            /* Setting XML header */
            @header ("content-type: text/xml charset=UTF-8");
            
            /* Initializing the XML Object */
            $xml = new XmlWriter();
            $xml->openMemory();
            $xml->setIndent(true);
            $xml->setIndentString('    ');
            $xml->startDocument('1.0', 'UTF-8');
            if(isset($xsltPath))
                $xml->WritePi('xml-stylesheet', 'type="text/xsl" href="'.$xsltPath.'"');
            $xml->startElement('callback');
            $xml->writeAttribute('xmlns:xsi','http://www.w3.org/2001/XMLSchema-instance');
            $xml->writeAttribute('xsi:noNamespaceSchemaLocation','schema.xsd');
            
            /* Function that converts each array element to an XML node */
            function write(XMLWriter $xml, $data){
                    foreach($data as $key => $value){
                            if(is_array($value)){
                                if (is_numeric($key)){   #The only time a numeric key would be used is if it labels an array with non-uniqe keys
                                    write($xml, $value);
                                    continue;
                                } else{
                                    $xml->startElement($key);
                                    write($xml, $value);
                                    $xml->endElement();
                                    continue;
                                }
                            }
                            $xml->writeElement($key, $value);
                    }
            }
            
            /* Calls previously declared function, passing our results array as parameter */
            write($xml, $results);
            
            /* Closing last XML node */
            $xml->endElement();
            
            /* Printing the XML */
            echo $xml->outputMemory(true);
        }
                        
        function outputKml($results){
            if (strtolower($_GET['action']) == 'get'){
                include('FormatKml.php');
                FormatKml::output($results);
            }else{
                $results['head']['warning'] .= 'KML is only a valid format for the "get" action; defaulting to xml. ';
                self::outputXml($results);
            }
        }
                        
        function outputWiki($results){
            if (strtolower($_GET['action']) == 'get'){
                include('FormatWikilist.php');
                FormatWikilist::output($results);
            }else{
                $results['head']['warning'] .= 'wikilist is only a valid format for the "get" action; defaulting to xml. ';
                self::outputXml($results);
            }
        }
        
        function outputGeojson($results){
            if (strtolower($_GET['action']) == 'get'){
                include('FormatGeojson.php');
                $full = False;
                $compact = False;
                if (strtolower($_GET['geojson']) == 'full'){
                    $full=True;
                }
                if (strtolower($_GET['json']) == 'compact'){
                    $compact=True;
                }
                FormatGeojson::output($results, $full, $compact);
            }else{
                $results['head']['warning'] .= 'geojson is only a valid format for the "get" action; defaulting to xml. ';
                self::outputXml($results);
            }
        }
        
        function outputDefault($results){
            self::outputXml($results);
        }
        
        #quick and dirty
        function outputXsl($results){
            if (strtolower($_GET['action']) == 'get')
                self::outputXml($results, 'get.xsl');
            elseif ((strtolower($_GET['action']) == 'admin') and (strtolower($_GET['function']) == 'diff'))
                self::outputXml($results, 'diff.xsl');
            elseif ((strtolower($_GET['action']) == 'admin') and (strtolower($_GET['function']) == 'info'))
                self::outputXml($results, 'info.xsl');
            else{
                $results['head']['warning'] .= 'XSL is only a valid format for the "get" and "admin/diff" actions; defaulting to xml. ';
                self::outputXml($results);
            }
        }
        
    }
?>
