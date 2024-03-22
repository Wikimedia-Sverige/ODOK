<?php
    /*
     * Entry point for api
     *
     */
    #dynamickml does not require a proper search. Just return the output.
    if(key_exists('format', $_GET) and $_GET['format']=='dynamickml') {
        include('FormatDynamicKml.php');
        FormatDynamicKml::output();
    } elseif(key_exists('format', $_GET) and $_GET['format']=='googlemaps') {
        include('FormatDynamicKml.php');
        GoogleMaps::output();
    } else {
        include('ApiMain.php');
        ApiMain::search();
    }
?>
