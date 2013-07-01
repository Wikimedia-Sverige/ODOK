<?php

/**
 * KML network link generation
 * modification of: https://fisheye.toolserver.org/browse/erfgoed/api/includes/DynamicKml.php
 **/

class GoogleMaps {
    function output() {
        $request_url = "http://$_SERVER[HTTP_HOST]$_SERVER[REQUEST_URI]";
        $kml_url = urlencode( str_replace('format=googlemaps', 'format=dynamickml', $request_url) );
        header( 'Location: https://maps.google.com/maps?q='.$kml_url.'&hl=sv&ll=63.470145,23.378906&z=4' ) ;    
    }
}


class FormatDynamicKml {

    function output() {
        header( "Content-Type: application/vnd.google-earth.kml+xml" );
        $request_url = "http://$_SERVER[HTTP_HOST]$_SERVER[REQUEST_URI]";
        $replCount = 1;
        $kml_url = htmlspecialchars( str_replace('format=dynamickml', 'format=kml', $request_url, $replCount) );
        $desc = 'Öppen databas över offentlig konst i Sverige för <a 
href="https://se.wikimedia.org/wiki/Projekt:Öppen_databas_för_offentlig_konst">Wikimedia Sverige</a>';
        $desc = htmlspecialchars( $desc );
        $folderName = 'Offentlig konst i Sverige';
        $folderName = htmlspecialchars( $folderName );
        $linkName = 'Konstverk';
        $linkName = htmlspecialchars( $linkName );
        echo '<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">
 <Folder>
  <name>'. $folderName .'</name>
  <open>1</open>
  <Snippet></Snippet>
  <description>'. $desc .'</description>
  <NetworkLink>
   <name>'. $linkName .'</name>
   <visibility>1</visibility>
   <open>0</open>
   <Link>
    <href>' . $kml_url .'</href>
    <viewRefreshMode>onStop</viewRefreshMode>
    <viewRefreshTime>1</viewRefreshTime>
    <viewFormat>bbox=[bboxWest],[bboxSouth],[bboxEast],[bboxNorth]</viewFormat>
    <viewBoundScale>0.9</viewBoundScale>
   </Link>
  </NetworkLink>
 </Folder>
</kml>
';
    }

}
