<?php	
	/*
	 * Entry point for api
	 *
	 */
	#dynamickml does not require a proper search. Just return the output.
	if($_GET['format']=='dynamickml'){
		include('FormatDynamicKml.php');
		FormatDynamicKml::output();
	}
	elseif($_GET['format']=='googlemaps'){
		include('FormatDynamicKml.php');
		GoogleMaps::output();
	}
	else{
		include('ApiMain.php');
		ApiMain::search();
	}
?>
