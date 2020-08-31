var muni; // contains muni code to name conversion
var rObjs = [];
var map;
var markers; // this is actually the featureGroup
var allMarkers = [];
var toManyResults = 100;
var thumb_width = 100;
var specialIcon;
var normalIcon;
var messages = {
    "no_results": "Inga träffar hittades. Försök ändra i din sökning",
    "to_many_results": "Sökningen fick {toManyResults}+ träffar, du vill antalgigen begränsa den på något sätt",
    "no_title": "[Ingen titel i databasen]",
    "no_coord": "Detta verk saknar koordinater",
    "no_image": "Detta verk saknar bild",
    "on_wiki": "Läs om det på Wikipedia",
    "osmSE_attrib": "Kartdata © {OSM_link}-bidragsgivare, kartrendering av {OSM_Sweden}",
    "year_warning": "Tillkomstår måste vara ett årtal",
    "year_negative_range": "Från måste vara större än Till i spannet för tillkomstår",
    "removed": "borttagen",
    "edit": "Redigera denna information på Wikipedia"
};

function executeSearch(a, t, m, c, i, yf, yt) {
    // a = artist
    // t = title
    // m = muni
    // c = coord
    // i = image
    // yf = year_from
    // yt = year_til

    console.log('ai: ' + a +
                ', ti: ' + t +
                ', mi: ' + m +
                ', ci: ' + c +
                ', ii: ' + i +
                ', yf: ' + yf +
                ', yt: ' + yt);

    rObjs = [];
    warnings = '';
    url = "http://offentligkonst.se/api/api.php?" +
          "action=get" +
          "&limit=" + toManyResults +
          "&has_same=false";
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
    // test if yf and yt are indeed integers
    // url needs to know if one or both are specified
    if(yf){
        if(!isInteger(yf)){
            warnings = messages.year_warning;
        }
        if(yt){
            if(!isInteger(yt)){
                warnings = messages.year_warning;
            }
            else if(parseInt(yf)>parseInt(yt)){
                warnings = messages.year_negative_range;
            }
            url += "&year=" + yf + "|" + yt;
        }
        else{
            url += "&year=" + yf + "|";
        }
    }
    else if(yt){
        if(!isInteger(yt)){
            warnings = messages.year_warning;
        }
        url += "&year=|" + yt;
    }

    // check warnings, if any then don't perform search
    if(warnings){
        populateSearchResult({"head":{"warning":warnings},"body":""});
        return;
    }

    // disable before ajax
    $('#button_search').prop("disabled", true);
    console.log( "url: " + url );
    var jqxhr = $.getJSON( url +
              "&callback=?"
    )
    .always(function() {
        $('#button_search').prop("disabled", false);
        console.log('Search executed.');
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
    var run = true;

    // reset markers, bounds and searchresult
    $('#searchresults').html('');
    markers.clearLayers();
    $('#feedbackbox').empty();

    // handle errormsgs
    if(header.error_message) {
        $('#feedbackbox').append('<p>' + header.error_message + '</p>');
        run = false;
    }
    if(header.warning) {
        $('#feedbackbox').append('<p>' + header.warning + '</p>');
    }
    if(!body) {
        $('#feedbackbox').append('<p>' + messages.no_results + '</p>');
        run = false;
    }
    else if(body.length >= toManyResults) {
        $('#feedbackbox').append('<p>' + messages.to_many_results.replace('{toManyResults}',toManyResults) + '</p>');
    }

    // show only if there are any messages
    if(!$('#feedbackbox').is(':empty')){
        $('#feedbackbox').show().delay(5000).fadeOut();
    }
    if(!run){
        return;
    }

    // map.addLayer(markers);

    // iterate all result objects
    $.each(body, function(index, ro) {
    ro = ro.hit;
    var newCard = $(document.createElement('div'));
    newCard.attr('class', 'resultcard');
    newCard.attr('id', 'rc_' + index);

    $(newCard).mouseenter(function() {
        highlightCard('rc_' + index);
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
        imgLnk = 'https://commons.wikimedia.org/wiki/File:' + ro.image;
        newCard.append('<a href="' + imgLnk + '" target="_blank">' + imgSrc + '</a>');
    }
    else {
        newCard.append('<img src="images/noImage.svg" title="' + messages.no_image + '" alt="' + messages.no_image + '" class="nopic"/>');
    }

    var content = '';

    if(ro.title) {
        content += '<b>' + ro.title + '</b>';
    }
    else {
        content += '<b>' + messages.no_title + '</b>';
    }
    if (ro.removed) {
        content += ' (' + messages.removed + ')';
    }
    if(ro.artist) {
        content += '<p>' + ro.artist;
    }
    if(ro.year) {
        content += ' (' + ro.year + ')';
    }
    if(!ro.lat || !ro.lon) {
        newCard.append('<img src="images/noCoord.svg" title="' + messages.no_coord + '" alt="' + messages.no_coord + '" class="nopic"/>');
    }

    newCard.append(content);

    // console.log(newCard);
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
    if(ro.wiki) {
        bc.append('<p><a href="https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/' + ro.wiki + '" target="_blank">' + messages.on_wiki + '</a></p>');
    }
    if (ro.list) {
        editImg = '<img src="images/edit.svg" title="' + messages.edit + '" alt="' + messages.edit + '" class="edit"/>';
        editLnk = 'https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/' + ro.list;
        bc.append('<a href="' + editLnk + '" target="_blank">' + editImg + '</a>');
    }

    $('#rc_' + index).balloon({
        position: 'left',
        classname: 'rcballoon',
        css: { minWidth: '400px' },
        contents: bc });
    });

    // Adjust map zoom
    if(body.length > 0) {
        map.fitBounds(markers.getBounds(), {'maxZoom':16});
    }
}

function addMarker(id, lon, lat) {
    // console.log("Addded a marker at longitude: " + lon + " latitude: " + lat);
    var llmark = L.marker(L.latLng(lat, lon), {icon: normalIcon}).on('click', onMarkerClick);
    allMarkers[id] = llmark;//._leaflet_id;
    markers.addLayer(llmark);
}

function onMarkerClick(e) {
    var id = getKeyByValue(allMarkers, this);

    highlightMarker(id);
    highlightCard(id);

    $('#sidebarholder').animate({
        scrollTop: ($('#sidebarholder').scrollTop() +
                    $('.resultcard#'+id).offset().top -
                    parseFloat($('#searchresults').css('padding-top')))
    }, 1000);
}

function getKeyByValue(object, value) {
    // https://stackoverflow.com/questions/9907419
    for( var prop in object ) {
        if( object.hasOwnProperty( prop ) ) {
             if( object[ prop ] === value )
                 return prop;
        }
    }
}

function highlightCard(id) {
    $('.activeCard').removeClass( 'activeCard' );
    $('.resultcard#'+id).addClass( 'activeCard' );
}

function highlightMarker(id) {
    for(var locid in allMarkers) {
        // reset all markers
        allMarkers[locid].setIcon(normalIcon);
    }
    if (id in allMarkers) {
        allMarkers[id].setIcon(specialIcon);
    }
}

function zoomToMarker(lon, lat, zoomLevel) {
    map.panTo(L.latLng(lat, lon));
}

function isInteger(val) {
    if($.isNumeric(val) && Math.floor(val) == val){
        return true;
    }
    return false;
}

function triggerSearch() {
    var ai = $('#artist_input').val();
    var ti = $('#title_input').val();
    var mi = $('#muni_selector').val();
    var ci = $('#coord_input').is(":checked");
    var ii = $('#image_input').is(":checked");
    var yfi = $('#year_input_from').val();
    var yti = $('#year_input_til').val();

    executeSearch(ai, ti, mi, ci, ii, yfi, yti);
    if (mi){
        mi = mi.join(',');
    }
    window.location.hash = mi + '/' +
                           ai.replace(' ','_') + '/' +
                           ti.replace(' ','_') + '/' +
                           ci + '/' +
                           ii + '/' +
                           yfi + '/' +
                           yti;
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

    // load basic Leaflet map
    var bounds = [[55.2, 10.8], [69.1, 24.4]];
    map = L.map('main', {'zoomControl':false}).fitBounds(bounds);
    map.addControl(
        L.control.zoom({
            'zoomInTitle':'Zooma in',
            'zoomOutTitle':'Zooma ut'
        })
    );
    // settings for tile Layer
    var osmSE = L.tileLayer('https://{s}.tile.openstreetmap.se/hydda/full/{z}/{x}/{y}.png', {
        maxZoom: 18,
        subdomains: 'abc',
        attribution: messages.osmSE_attrib
                    .replace('{OSM_link}','<a href="https://openstreetmap.org">OpenStreetMap</a>')
                    .replace('{OSM_Sweden}','<a href="https://openstreetmap.se">OpenStreetMap Sweden</a>')
    }).addTo(map);
    // OSM SE is down due to server crash
    // map.addLayer(osmSE);

    // settings for OSM
    var osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: 'Kartdata © <a href="https://openstreetmap.org">OpenStreetMap</a>-bidragsgivare',
        maxZoom: 19,
    });
    // Defaulting to OSMF while OSM SE is down due to server crash
    map.addLayer(osm);

    markers = L.featureGroup();
    map.addLayer(markers);

    // set-up markers
    specialIcon = L.icon({
        iconUrl: 'images/selected.svg',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });
    normalIcon = L.icon({
        iconUrl: 'images/default.svg',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    // Trigger search on button click or enter in text input
    $('#button_search').click(function(){
        triggerSearch();
    });
    $('.enterTriggered input').keypress(function(e){
        if(e.which == 13) {
            triggerSearch();
        }
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
        $('#artist_input').val(hashparts[1].replace('_',' '));
        $('#title_input').val(hashparts[2].replace('_',' '));
        if (hashparts[3] == 'true'){
            $('#coord_input').prop('checked', true);
        }
        if (hashparts[4] == 'true'){
            $('#image_input').prop('checked', true);
        }
        $('#year_input_from').val(hashparts[5]);
        $('#year_input_til').val(hashparts[6]);

        jqxhrMuni.done(function(){ // needs to wait for load
            $.each(hashparts, function( index, value ) {
                if ($.inArray(value, ['', 'false', 'null']) < 0){
                    console.log('Triggered for hashpart: ' + value);
                    triggerSearch();
                    return false; // to break out of .each-loop
                }
            });
        });
    }
    console.log('Loaded.');

};
