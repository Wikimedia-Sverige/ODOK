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
    //load basic Leaflet map
    var map = L.map('map').setView([59.3145,18.0162], 12); //setView is overrriden by cluseter function

    //settings for MapQuest
    var mapQuest = L.tileLayer("http://{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png", {
        attribution: "&copy; <a href='//www.openstreetmap.org/'>OpenStreetMap</a> and contributors, under an <a href='//www.openstreetmap.org/copyright' title='ODbL'>open license</a>. Tiles Courtesy of <a href='//www.mapquest.com/'>MapQuest</a> <img src='//developer.mapquest.com/content/osm/mq_logo.png'>",
        maxZoom: 19,
        subdomains: ['otile1','otile2','otile3','otile4']
    });

    //settings for OSM Sweden
    var osmSE = L.tileLayer('http://{s}.tile.openstreetmap.se/hydda/full/{z}/{x}/{y}.png', {
        maxZoom: 18,
        subdomains: 'abc',
        attribution: 'Map data &copy; <a href="//www.openstreetmap.org">OpenStreetMap</a> contributors, Imagery by <a href="http://openstreetmap.se">OpenStreetMap Sweden</a>'
    }).addTo(map);
    map.addLayer(osmSE);

    //settings for OSM
    var osm = L.tileLayer("//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: 'Map data © <a href="//openstreetmap.org">OpenStreetMap</a> contributors',
        maxZoom: 19,
    });

    //set-up markers
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

    //geoJson, once it is loaded
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

        //Clustering
        console.log("And now I'm here");
        var markers = new L.MarkerClusterGroup({showCoverageOnHover: false});
        markers.addLayer(odokLayer);        // add it to the cluster group
        map.addLayer(markers);		        // add it to the map
        map.fitBounds(markers.getBounds()); //set view on the cluster extent

        //for layers control
        var baseMaps = {
            "MapQuest": mapQuest,
            "OSM": osm,
            "OSM Sweden": osmSE
        };
        var overlayMaps = {
            "clustered": markers,
            "individual": odokLayer
        };
        L.control.layers(baseMaps, overlayMaps).addTo(map);
    });

    // search
    var osmOptions = {text: 'Hitta'};
    var osmGeocoder = new L.Control.OSMGeocoder(osmOptions);
    map.addControl(osmGeocoder);
    
    // hHash
    var hash = new L.Hash(map);

    //Rightclick gives coords (for improving data)
    var popup = L.popup();
    function onMapClick(e) {
        popup
            .setLatLng(e.latlng)
            .setContent("You clicked the map at " + e.latlng.toString())
            .openOn(map);
    }
    map.on('contextmenu', onMapClick);
});

// create the popupcontents
function makePopup(feature) {
    // Based on https://stackoverflow.com/questions/10889954
    var properties = feature.properties;
    var desc = "";

    // code originally from updateFeatures.py
    // image
    if (properties.image) {
        var showImage = '';
        if (properties.spatial.inside == 1 && properties.free == 'unfree') {
            showImage = 'Commons-icon.svg';
        }
        else {
            showImage = properties.image.replace(/\s/g, '_');
        }
        desc += '<a href="http://commons.wikimedia.org/wiki/File:' + showImage + '" target="_blank">';
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
    desc += muni[properties.spatial.muni].full;
    if (properties.spatial.district) {
        desc += ' (' + properties.spatial.district + ')';
    }
    if (properties.spatial.address) {
        desc += ' - ' + properties.spatial.address;
    }
    desc += '</li></ul>';
    if (properties.image || properties.descriptions.wiki || properties.descriptions.descr) {
        desc += '<br clear="both"/>';
    }
    // description
    var jqxhr;
    if (properties.descriptions.wikidata) {
        desc += properties.descriptions.ingress;
        desc += '  <a href="https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/' + properties.descriptions.wikidata + '" target="_blank">';
        desc += 'Läs mer om konstverket på Wikipedia';
        desc += '</a>.';
    }
    else if (properties.descriptions.descr) {
        desc += properties.descriptions.descr;
    }

    return desc;

}
