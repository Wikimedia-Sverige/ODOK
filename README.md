ODOK
====

Code for Offentligkonst.se / ÖDOK (Öppen Databas för Offentlig Konst).

The project consists of a database, an open API, a webpage to display the database contents on a leaflet map along with a separate page for search. Also various tools for mainitaining these.

For more information see:

* https://se.wikimedia.org/wiki/Offentligkonst.se
* http://www.offentligkonst.se


## See also

* [HACK4DK](https://github.com/lokal-profil/HACK4DK) is a search engine which looks at the ÖDOK database along with similar databases in Norway and Denmark.


## Credits

* The search is forked from [lokal-profil/HACK4DK](https://github.com/lokal-profil/HACK4DK) by [fluffis](https://github.com/fluffis) and [lokal-profil](https://github.com/lokal-profil)
* [WikiApi](https://github.com/lokal-profil/ODOK/blob/master/tools/WikiApi.py) is based on PyCJWiki Version 1.31 (C) by [Smallman12q](https://en.wikipedia.org/wiki/User_talk:Smallman12q) GPL, see http://www.gnu.org/licenses/.
* The various plugins at *site/leaflet* and *site/external* are by several different authors and under different licenses, see the header of each file for source/credit info.
* The images in site/images are modified from:
  * search.svg: [Magnifyinglass.svg](https://commons.wikimedia.org/wiki/File:Magnifyinglass.svg) by MGalloway (WMF)
  * noImage.svg: [LockImage_icon.svg](https://commons.wikimedia.org/wiki/File:LockImage_icon.svg) by MGalloway (WMF)
  * edit.svg: [Edit icon.svg](https://commons.wikimedia.org/wiki/File:Edit_icon.svg) by MGalloway (WMF)
  * default.svg / selected.svg / noCoord.svg: [marker.svg](https://github.com/Leaflet/Leaflet/blob/master/src/images/marker.svg) by the Leaflet team
