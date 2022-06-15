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
        
        static function outputJsonp($results, $callback){
            /* Setting up JSONP headers */
            @header ("content-type: application/javascript; charset=utf-8");
            
            /* Printing the wrapped JSON Object */
            echo $callback.'('.json_encode($results).');';
        }
        
        static function outputJson($results){
            /* Setting up JSON headers */
            @header ("content-type: application/json; charset=utf-8");
            header ("Access-Control-Allow-Origin: *");

            $compact=False;
            if (key_exists('json', $_GET) and strtolower($_GET['json']) == 'compact'){
                $compact=True;
            }
            /* Printing the JSON Object */
            if ($compact){
                echo json_encode($results);
            }else{
                echo self::prettyPrintJson($results);
            }
        }
        
        static function outputPhp($results){   
            /* Setting up PHP headers */
            header ("content-type: application/x-php; charset=utf-8");
    
            /* Printing the PHP serialized Object*/
            echo serialize($results);
        }
                
        static function outputXml($results, $xsltPath=null){
            /* Setting XML header */
            @header ("content-type: text/xml; charset=UTF-8");
            
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
            if($results) {
                write($xml, $results);
            }
            
            /* Closing last XML node */
            $xml->endElement();
            
            /* Printing the XML */
            echo $xml->outputMemory(true);
        }
                        
        static function outputKml($results){
            if (strtolower($_GET['action']) == 'get'){
                include('FormatKml.php');
                FormatKml::output($results);
            }else{
                $results['head']['warning'] .= 'KML is only a valid format for the "get" action; defaulting to xml. ';
                self::outputXml($results);
            }
        }
                        
        static function outputWiki($results){
            if (strtolower($_GET['action']) == 'get'){
                include('FormatWikilist.php');
                FormatWikilist::output($results);
            }else{
                $results['head']['warning'] .= 'wikilist is only a valid format for the "get" action; defaulting to xml. ';
                self::outputXml($results);
            }
        }
        
        static function outputGeojson($results){
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
        
        static function outputDefault($results){
            self::outputXml($results);
        }
        
        #quick and dirty
        static function outputXsl($results){
            if (strtolower($_GET['action']) == 'get')
                self::outputXml($results, 'get.xsl');
            elseif (strtolower($_GET['action']) == 'artist')
                self::outputXml($results, 'artist.xsl');
            elseif ((strtolower($_GET['action']) == 'admin') and (strtolower($_GET['function']) == 'diff'))
                self::outputXml($results, 'diff.xsl');
            elseif ((strtolower($_GET['action']) == 'admin') and (strtolower($_GET['function']) == 'info'))
                self::outputXml($results, 'info.xsl');
            else{
                $results['head']['warning'] .= 'XSL is only a valid format for the "get" and "admin/diff" actions; defaulting to xml. ';
                self::outputXml($results);
            }
        }
        
        #For backwards compatibility wiht PHP versions below 5.4
        #Code by Kendall Hopkins @ http://stackoverflow.com/questions/6054033/pretty-printing-json-with-php
        static function prettyPrintJson( $results ){
            if (version_compare(PHP_VERSION, '5.4.0') >= 0) {
                return json_encode($results, JSON_PRETTY_PRINT);
            }else{
                return self::prettyPrint(json_encode($results));
            }
        }
        
        static function prettyPrint( $json )
        {
            $result = '';
            $level = 0;
            $prev_char = '';
            $in_quotes = false;
            $ends_line_level = NULL;
            $json_length = strlen( $json );
        
            for( $i = 0; $i < $json_length; $i++ ) {
                $char = $json[$i];
                $new_line_level = NULL;
                $post = "";
                if( $ends_line_level !== NULL ) {
                    $new_line_level = $ends_line_level;
                    $ends_line_level = NULL;
                }
                if( $char === '"' && $prev_char != '\\' ) {
                    $in_quotes = !$in_quotes;
                } else if( ! $in_quotes ) {
                    switch( $char ) {
                        case '}': case ']':
                            $level--;
                            $ends_line_level = NULL;
                            $new_line_level = $level;
                            break;
        
                        case '{': case '[':
                            $level++;
                        case ',':
                            $ends_line_level = $level;
                            break;
        
                        case ':':
                            $post = " ";
                            break;
        
                        case " ": case "\t": case "\n": case "\r":
                            $char = "";
                            $ends_line_level = $new_line_level;
                            $new_line_level = NULL;
                            break;
                    }
                }
                if( $new_line_level !== NULL ) {
                    $result .= "\n".str_repeat( "\t", $new_line_level );
                }
                $result .= $char.$post;
                $prev_char = $char;
            }
        
            return $result;
        }
        
    }
?>
