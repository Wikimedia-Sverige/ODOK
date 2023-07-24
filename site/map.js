var muni = ''; // contains muni code to name conversion
var features = '';

$(document).ready(function() {
    // load muni json into variable
    var jqxhrMuni = $.getJSON("./muni.json", function( data ) {
        muni = data;
    });
    // load features json into variable
    var jqxhrFeat = $.getJSON("./AllFeatures.geo.json", function( data ) {
        features = data;
            console.log("popup-features.head.hits: " + features.head.hits);
    });

    // set up map
    // load basic Leaflet map
    var bounds = [[55.2, 10.8], [69.1, 24.4]];
    var map = L.map('map', {'zoomControl':false}).fitBounds(bounds);
    map.addControl(
        L.control.zoom({
            'zoomInTitle':'Zooma in',
            'zoomOutTitle':'Zooma ut'
        })
    );

    var attribution = 'Ett projekt från <a href="//wikimedia.se/">Wikimedia Sverige</a> med stöd av <a href="http://www.vinnova.se">Vinnova</a>. | ';

    // settings for OSM Sweden
    var osmSE = L.tileLayer('https://{s}.tile.openstreetmap.se/hydda/full/{z}/{x}/{y}.png', {
        maxZoom: 18,
        subdomains: 'abc',
        attribution: attribution + 'Kartdata © <a href="https://openstreetmap.org">OpenStreetMap</a>-bidragsgivare, kartrendering av <a href="https://openstreetmap.se">OpenStreetMap Sweden</a>'
    }).addTo(map);
    // OSM SE is down due to server crash
    // map.addLayer(osmSE);

    // settings for OSM
    var osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: attribution + 'Kartdata © <a href="https://openstreetmap.org">OpenStreetMap</a>-bidragsgivare',
        maxZoom: 19,
    });
    // Defaulting to OSMF while OSM SE is down due to server crash
    map.addLayer(osm);

    // set-up markers
    var noPicIcon = L.icon({
        iconUrl: 'images/withoutimageicon.png',
        iconSize: [32, 32],
        iconAnchor: [16, 31],
        popupAnchor: [0, -16]
    });
    var picIcon = L.icon({
        iconUrl: 'images/withimageicon.png',
        iconSize: [32, 32],
        iconAnchor: [16, 31],
        popupAnchor: [0, -16]
    });

    // reduce size of attribution text on small displays (also on resize)
    if ($(window).width() < 500) {
        $(".leaflet-control-attribution").css({"font-size": "9px"});
        console.log('setting size to 9');
    }
    $(window).on('resize', function() {
        if ($(window).width() >= 500) {
            $(".leaflet-control-attribution").removeAttr("style");
            console.log('resetting size');
        }
        else if ($(window).width() < 500) {
            $(".leaflet-control-attribution").css({"font-size": "9px"});
            console.log('setting size to 9');
        }
        console.log('Window resized to: ' + $(window).width());
    });

    // geoJson, once it is loaded
    jqxhrFeat.complete( function() {
        var odokLayer = L.geoJson(features, {
            onEachFeature: function (feature, layer) {
                layer.bindPopup(makePopup(feature));
            },
            pointToLayer: function (feature, latlng) {
                if (feature.properties.image){
                    return L.marker(latlng, {icon: picIcon, title:feature.properties.title });
                }else{
                    return L.marker(latlng, {icon: noPicIcon, title:feature.properties.title });
                }
            }
        });

        // Clustering
        var markers = new L.MarkerClusterGroup({showCoverageOnHover: false});
        markers.addLayer(odokLayer);        // add it to the cluster group
        map.addLayer(markers);		        // add it to the map
        // commented out since it overrides the hash
        // map.fitBounds(markers.getBounds()); //set view on the cluster extent

        // for layers control
        var baseMaps = {
            "OSM": osm,
            "OSM Sweden": osmSE
        };
        var overlayMaps = {
            "kluster": markers,
            "individuella": odokLayer
        };
        L.control.layers(baseMaps, overlayMaps).addTo(map);
    });

    // search
    var osmOptions = {text: 'Sök plats'};
    var osmGeocoder = new L.Control.OSMGeocoder(osmOptions);
    map.addControl(osmGeocoder);

    // locate
    L.control.locate({
        position: 'topleft',  // set the location of the control
        drawCircle: true,  // controls whether a circle is drawn that shows the uncertainty about the location
        icon: 'fa fa-crosshairs',  // class for icon, fa-location-arrow or fa-map-marker
        metric: true,  // use metric or imperial units
        showPopup: true, // display a popup when the user click on the inner marker
        strings: {
            title: "Visa var jag är",  // title of the locate control
            popup: "Du är inom {distance} meter från denna punkt",  // text to appear if user clicks on circle
            outsideMapBoundsMsg: "Du verkar befinna dig utanför kartans gränser" // default message for onLocationOutsideMapBounds
        },
        locateOptions :{
            maxZoom: 16
        }
    }).addTo(map);

    // Hash
    var hash = new L.Hash(map);

    // Right-click gives coords (for improving data)
    var popup = L.popup();
    function onMapClick(e) {
        popup
            .setLatLng(e.latlng)
            .setContent("Du klickade på koordinaten: <br />" + e.latlng.lat.toFixed(6) + ", " + e.latlng.lng.toFixed(6))
            .openOn(map);
    }
    map.on('contextmenu', onMapClick);

    // center popup AND marker to the map + 23% of clientHeight
    // to position it under the leaflet-control-locate icon on small displays
    function centerOnSmall(e) {
        if ($(window).width() <= 380){
            var px = map.project(e.popup._latlng); // find the pixel location on the map where the popup anchor is
            px.y -= e.popup._container.clientHeight/2+e.popup._container.clientHeight*0.23; // find the height of the popup container, divide by 2, subtract from the Y axis of marker location
            map.panTo(map.unproject(px),{animate: true}); // pan to new center
        }
    }
    map.on('popupopen', centerOnSmall);
});

// create the popupcontents
function makePopup(feature) {
    // Based on https://stackoverflow.com/questions/10889954
    var properties = feature.properties;
    var desc = "";

    // code originally from updateFeatures.py
    // list-link
    if (properties.descriptions.list) {
        desc += '<a href="https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/' + properties.descriptions.list + '" target="_blank">';
        desc += '<img src="images/edit.svg" title="Uppdatera informationen om verket på Wikipedia" alt="Uppdatera informationen om verket på Wikipedia" class="edit"/>';
        desc += '</a>';
    }

    // image
    if (properties.image) {
        var showImage = '';
        if (properties.spatial.inside == 1 && properties.free == 'unfree') {
            showImage = 'Commons-icon.svg';
        }
        else {
            showImage = properties.image.replace(/\s/g, '_');
        }
        desc += '<a href="https://commons.wikimedia.org/wiki/File:' + showImage + '" target="_blank">';
        desc += '<img src="https://commons.wikimedia.org/w/thumb.php?f=' + showImage + '&width=100" class="thumb" />';
        desc += '</a>';

        // info
    }
    desc += '<ul>';
    if (properties.title) {
        desc += '<li> '; //title
        desc += '<b>' + properties.title + '</b>';
        desc += '</li>';
    }

    // artist - year
    desc += '<li> ';
    if (properties.artist) {
        $.each(properties.artist, function(index, ai) {
            if (ai.wikidata) {
                desc += '<a href="https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/' + ai.wikidata + '" target="_blank">';
                desc += ai.name;
                desc += '</a>';
            }
            else {
                desc += ai.name;
            }
            desc += ', ';
        });
        desc = desc.slice(0,-2); // remove trailing ", "
    }
    else {
        desc += '<i>Okänd konstnär</i>';
    }
    if (properties.year) {
        desc += ' - ' + properties.year;
    }

    // Muni - address
    desc += '</li><li> ';
    if (muni[properties.spatial.muni]) {
        desc += muni[properties.spatial.muni].full;
    }
    else {
        console.log("Object has weird muni. Id: " + properties.id + " muni: " + properties.spatial.muni);
    }
    if (properties.spatial.district) {
        desc += ' (' + properties.spatial.district + ')';
    }
    if (properties.spatial.address) {
        desc += ' - ' + properties.spatial.address;
    }

    // description
    desc += '</li><li> ';
    if (properties.descriptions.wikidata) {
        desc += properties.descriptions.ingress;
        desc += '  <a href="https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/' + properties.descriptions.wikidata + '" target="_blank">';
        desc += 'Läs mer om konstverket på Wikipedia';
        desc += '</a>.';
    }
    else if (properties.descriptions.descr) {
        desc += capitalizeFirstLetter(properties.descriptions.descr);
    }

    if (properties.image || properties.descriptions.wikidata || properties.descriptions.descr) {
        desc += '<br clear="both"/>';
    }
    desc += '</li></ul>';
    return desc;

}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}
