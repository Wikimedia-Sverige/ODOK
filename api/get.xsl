<?xml version="1.0" encoding="UTF-8"?>
<!-- add <?xml-stylesheet type="text/html" href="get.xsl"?> to xml just after xml declaration-->
<xsl:stylesheet version="1.0"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:template match="/">
    <xsl:choose>
        <xsl:when test="callback/head/status=1">
            <xsl:call-template name="Display_Success"/>
        </xsl:when>
        <xsl:otherwise>
            <xsl:call-template name="Display_Fail"/>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

<!-- **************Display_Success****************************************** -->
<xsl:template name="Display_Success">
  <html>
  <body>
    <h2>Result</h2>
    Status: <xsl:value-of select="callback/head/status"/><br/>
    Hits: <xsl:value-of select="callback/head/hits"/><br/>
    Limit: <xsl:value-of select="callback/head/limit"/><br/>
    <xsl:if test="callback/head/warning != ''">
        Warning: <xsl:value-of select="callback/head/warning"/><br/>
    </xsl:if>
    <table border="1">
      <tr bgcolor="#9acd32">
        <th>ID</th>
        <th>Title</th>
        <th>Artist</th>
        <th>Description</th>
        <th>Year</th>
        <th>Year comment</th>
        <th>Type</th>
        <th>Material</th>
        <th>Inside</th>
        <th>Address</th>
        <th>County</th>
        <th>Municipality</th>
        <th>District</th>
        <th>Coord (lat, lon)</th>
        <th>Removed</th>
        <th>Image (link)</th>
        <th>Source</th>
        <th>UGC</th>
        <th>Changed</th>
        <th>Created</th>
        <th>Article (link)</th>
        <th>List (link)</th>
        <th>Commons category (link)</th>
        <th>Official url</th>
        <th>Same_as</th>
        <th>Free</th>
        <th>Owner</th>
      </tr>
      <xsl:for-each select="callback/body/hit">
            <tr>
              <td><xsl:value-of select="id"/></td>
              <td><xsl:value-of select="title"/></td>
              <td><xsl:value-of select="artist"/></td>
              <td><xsl:value-of select="descr"/></td>
              <td><xsl:value-of select="year"/></td>
              <td><xsl:value-of select="year_cmt"/></td>
              <td><xsl:value-of select="type"/></td>
              <td><xsl:value-of select="material"/></td>
              <td><xsl:call-template name="Display_Bool">
                      <xsl:with-param name="bool">
                          <xsl:value-of select="inside"/>
                      </xsl:with-param>
                  </xsl:call-template></td>
              <td><xsl:value-of select="address"/></td>
              <td><xsl:value-of select="county"/></td>
              <td><xsl:value-of select="muni"/></td>
              <td><xsl:value-of select="district"/></td>
              <td><small>(<xsl:value-of select="lat"/>, <xsl:value-of select="lon"/>)</small></td>
              <td><xsl:call-template name="Display_Bool">
                      <xsl:with-param name="bool">
                          <xsl:value-of select="removed"/>
                      </xsl:with-param>
                  </xsl:call-template></td>
              <td><xsl:call-template name="Display_Image-link"/></td>
              <td><xsl:value-of select="source"/></td>
              <td><xsl:call-template name="Display_Bool">
                      <xsl:with-param name="bool">
                          <xsl:value-of select="ugc"/>
                      </xsl:with-param>
                  </xsl:call-template></td>
              <td><xsl:value-of select="changed"/></td>
              <td><xsl:value-of select="created"/></td>
              <td><xsl:call-template name="Display_Wikidata-link">
                      <xsl:with-param name="wdID">
                          <xsl:value-of select="wiki"/>
                      </xsl:with-param>
                  </xsl:call-template></td>
              <td><xsl:call-template name="Display_Wikidata-link">
                      <xsl:with-param name="wdID">
                          <xsl:value-of select="list"/>
                      </xsl:with-param>
                  </xsl:call-template></td>
              <td><xsl:call-template name="Display_Cat-link"/></td>
              <td><xsl:value-of select="official_url"/></td>
              <td><xsl:value-of select="same_as"/></td>
              <td><xsl:value-of select="free"/></td>
              <td><xsl:value-of select="owner"/></td>
            </tr>
      </xsl:for-each>
  </table>
  </body>
  </html>
</xsl:template>
<!-- **************Display_Fail****************************************** -->
<xsl:template name="Display_Fail">
    <html>
    <body>
        <h2>Result</h2>
        Status: <xsl:value-of select="callback/head/status"/><br/>
        Error_number: <xsl:value-of select="callback/head/error_number"/><br/>
        Error_message: <xsl:value-of select="callback/head/error_message"/><br/>
        <xsl:if test="callback/head/warning != ''">
            Warning: <xsl:value-of select="callback/head/warning"/><br/>
        </xsl:if>
    </body>
    </html>
</xsl:template>

<!-- **************Sub-Templates****************************************** -->
<xsl:template name="Display_Cat-link">
    <a><xsl:attribute name="href">
        http://commons.wikimedia.org/wiki/Category:<xsl:value-of select="commons_cat"/></xsl:attribute>
        <xsl:value-of select="commons_cat"/>
    </a>
</xsl:template>
<xsl:template name="Display_Image-link">
    <a><xsl:attribute name="href">
        http://commons.wikimedia.org/wiki/File:<xsl:value-of select="image"/></xsl:attribute>
        <xsl:value-of select="image"/>
    </a>
</xsl:template>
<xsl:template name="Display_Wikidata-link">
    <xsl:param name="wdID" />
    <a><xsl:attribute name="href">
        https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/<xsl:value-of select="$wdID"/></xsl:attribute>
        <xsl:value-of select="$wdID"/>
    </a>
</xsl:template>
<xsl:template name="Display_Bool">
    <xsl:param name="bool" />
    <xsl:choose>
        <xsl:when test="$bool=1">
            &#10004;
        </xsl:when>
        <xsl:otherwise>
            &#10008;
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

</xsl:stylesheet>
