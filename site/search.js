var muni; // contains muni code to name conversion
var rObjs = [];
var map;
var markers; // this is actually the featureGroup
var allMarkers = [];
var toManyResults=100;
var thumb_width=100;
var specialIcon;
var normalIcon;
var messages = {
    "no_results": "Inga träffar hittades. Försök ändra i din sökning",
    "to_many_results": "Sökningen fick {toManyResults}+ träffar, du vill antalgigen begränsa den på något sätt",
    "no_title": "[Ingen titel i databasen]",
    "no_coord": "Detta verk saknar koordinater",
    "no_image": "Detta verk saknar bild",
    "on_wiki": "Läs om det på Wikipedia",
    "osmSE_attrib": "Kartdata © {OSM_link}-bidragsgivare, kartrendering av {OSM_Sweden}"
};

function executeSearch(a, t, m, c, i) {
    // a = artist
    // t = title
    // m = muni
    // c = coord
    // i = image

    console.log('ai: ' + a + ', ti: ' + t + ', mi: ' + m + ', ci: ' + c + ', ii: ' + i);

    rObjs = [];
    url = "http://offentligkonst.se/api/api.php?" +
          "action=get" +
          "&limit=" + toManyResults;
    if(a){
        url += "&artist=" + a;
    }
    if(t){
        url += "&title=" + t;
    }
    if(m){
        url += "&muni=" + m.join("|");
    }
    if(c){
        url += "&has_coords=true";
    }
    if(i){
        url += "&has_image=true";
    }
    //disable before ajax
    $('#button_search').prop("disabled", true);
    console.log( "url: " + url );
    var jqxhr = $.getJSON( url +
              "&callback=?"
    )
    .always(function() {
        $('#button_search').prop("disabled", false);
    })
    .done(function(json) {
        populateSearchResult(json);
    })
    .fail(function(jqXHR, textStatus) {
        console.log('An error occurred while loading data (AJAX error ' + textStatus + ')');
    });

}


function populateSearchResult(rObjs) {

    var header = rObjs.head;
    var body = rObjs.body;

    // reset markers, bounds and searchresult
    $('#searchresults').html('');
    markers.clearLayers();

    // handle errormsgs
    if(header.error_message) {
        $('#feedbackbox').html('<p>' + header.error_message + '</p>').show().delay(5000).fadeOut();
    }

    if(header.warning) {
        $('#feedbackbox').html('<p>' + header.warning + '</p>').show().delay(5000).fadeOut();
    }
    if(!body) {
        $('#feedbackbox').html('<p>' + messages.no_results + '</p>').show().delay(5000).fadeOut();
        return;
    }
    else if(body.length >= toManyResults) {
        $('#feedbackbox').html('<p>' + messages.to_many_results.replace('{toManyResults}',toManyResults) + '</p>').show().delay(5000).fadeOut();
    }


    //map.addLayer(markers);

    // iterate all result objects
    $.each(body, function(index, ro) {
    ro = ro.hit;
    var newCard = $(document.createElement('div'));
    newCard.attr('class', 'resultcard');
    newCard.attr('id', 'rc_' + index);

    $(newCard).mouseenter(function() {
        highlightMarker('rc_' + index);
        if(ro.lat && ro.lon) {
            zoomToMarker(ro.lon, ro.lat, 13);
        }
        else {
            $('#main').removeClass('hascoord')
                .addClass('nocoord');
        }
    });
    if(!ro.lat || !ro.lon) {
        $(newCard).mouseout(function() {
            $('#main').removeClass('nocoord')
                .addClass('hascoord');
        });
    }
    if(ro.lat && ro.lon) {
        addMarker('rc_' + index, ro.lon, ro.lat);
    }


    if(ro.image) {
        imgSrc = '<img src="https://commons.wikimedia.org/w/thumb.php?f=' + ro.image +
                 '&width=' + thumb_width + '" class="thumb" />';
        imgLnk = 'https://commons.wikimedia.org/wiki/ro.image';
        newCard.append('<a href="' + imgLnk + '" target="_blank">' + imgSrc + '</a>');
    }
    else {
        newCard.append('<img src="/images/noImage.svg" title="' + messages.no_image + '" alt="' + messages.no_image + '" class="nopic"/>');
    }

    var content = '';

    if(ro.title) {
        content += '<b>' + ro.title + '</b>';
    }
    else {
        content += '<b>' + messages.no_title + '</b>';
    }
    if(ro.artist) {
        content += '<p>' + ro.artist;
    }
    if(ro.year) {
        content += ' (' + ro.year + ')';
    }
    if(!ro.lat || !ro.lon) {
        newCard.append('<img src="/images/noCoord.svg" title="' + messages.no_coord + '" alt="' + messages.no_coord + '" class="nopic"/>');
    }

    newCard.append(content);

//  console.log(newCard);
    $('#searchresults').append(newCard);

    var bc = $(document.createElement('div'));
    bc.append(newCard.html());

    if(ro.material) {
            bc.append('<p>' + ro.material);
    }

    var place = '';
    if (ro.muni) {
        place += muni[ro.muni].full;
    }
    if (ro.district) {
        place += ' (' + ro.district + ')';
    }
    if (ro.address) {
        place += ' - ' + ro.address;
    }
    if(place) {
            bc.append('<p>' + place);
    }
    if(ro.wiki_article) {
        bc.append('<p><a href="https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/' + ro.wiki_article + '" target="_blank">' + messages.on_wiki + '</a></p>');
    }

    $('#rc_' + index).balloon({
        position: 'left',
        classname: 'rcballoon',
        css: { minWidth: '400px' },
        contents: bc });
    });

    // Adjust map zoom
    if(body.length > 0) {
        map.fitBounds(markers.getBounds());
    }
}

function addMarker(id, lon, lat) {
    console.log("Addded a marker at longitude: " + lon + " latitude: " + lat);
    var llmark = L.marker(L.latLng(lat, lon), {icon: normalIcon});
    allMarkers[id] = llmark;//._leaflet_id;
    markers.addLayer(llmark);
}

function highlightMarker(id) {
    for(var locid in allMarkers) {
        //reset all markers
        allMarkers[locid].setIcon(normalIcon);
    }
    if (id in allMarkers) {
        allMarkers[id].setIcon(specialIcon);
    }
}

function zoomToMarker(lon, lat, zoomLevel) {
    map.panTo(L.latLng(lat, lon));
}


window.onload = function load() {
    // load muni json into variable and populate selectorlist
   var jqxhrMuni = $.getJSON("./muni.json",
        function( data ) {
            muni = data;
            $.each(muni, function(key, value) {
                $('#muni_selector')
                    .append($('<option />')
                    .val(key)
                    .text(value.full));
            });
            $('#muni_selector').chosen();
    });

    // Load map from OSM
    map = L.map('main', {'zoomControl':false}).setView([63.5,16.9], 4);
    map.addControl(
        L.control.zoom({
            'zoomInTitle':'Zooma in',
            'zoomOutTitle':'Zooma ut'
        })
    );
    //settings for tile Layer
    var osmSE = L.tileLayer('http://{s}.tile.openstreetmap.se/hydda/full/{z}/{x}/{y}.png', {
        maxZoom: 18,
        subdomains: 'abc',
        attribution: messages.osmSE_attrib
                    .replace('{OSM_link}','<a href="//openstreetmap.org">OpenStreetMap</a>')
                    .replace('{OSM_Sweden}','<a href="http://openstreetmap.se">OpenStreetMap Sweden</a>')
    }).addTo(map);
    map.addLayer(osmSE);

    markers = L.featureGroup();
    map.addLayer(markers);

    //set-up markers
    specialIcon = L.icon({
        iconUrl: 'images/selected.svg'
    });
    normalIcon = L.icon({
        iconUrl: 'images/default.svg'
    });

    // Trigger search
    $('#button_search').click(function(){
       var ai = $('#artist_input').val();
       var ti = $('#title_input').val();
       var mi = $('#muni_selector').val();
       var ci = $('#coord_input').is(":checked");
       var ii = $('#image_input').is(":checked");

       executeSearch(ai, ti, mi, ci, ii);
       console.log('Search executed.');
       if (mi){
           mi = mi.join(',');
       }
       window.location.hash = mi + '/' + ai + '/' + ti + '/' + ci + '/' + ii;
    });

    // Handle incoming hash
    var hash = $(location).attr('hash').substring(1);
    if(hash) {
        // muni/artist/title
        var hashparts = hash.split("/");
        jqxhrMuni.done(function(){
            $.each(hashparts[0].split(","), function(i,e){
                $("#muni_selector option[value='" + e + "']")
                    .prop("selected", true);
            });
            $("#muni_selector").trigger("chosen:updated");
        });
        $('#artist_input').val(hashparts[1]);
        $('#title_input').val(hashparts[2]);
        if (hashparts[3] == 'true'){
            $('#coord_input').prop('checked', true);
        }
        if (hashparts[4] == 'true'){
            $('#image_input').prop('checked', true);
        }

    }
    console.log('Loaded.');

};
