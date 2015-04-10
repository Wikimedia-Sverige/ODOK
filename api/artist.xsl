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
        <th>First name</th>
        <th>Last name</th>
        <th>Article (link)</th>
        <th>Birth date (year)</th>
        <th>Death date (year)</th>
        <th>Creator template</th>
        <th>Works</th>
        <th>Changed</th>
      </tr>
      <xsl:for-each select="callback/body/hit">
            <tr>
              <td><xsl:value-of select="id"/></td>
              <td><xsl:value-of select="first_name"/></td>
              <td><xsl:value-of select="last_name"/></td>
              <td><xsl:call-template name="Display_Wikidata-link">
                      <xsl:with-param name="wdID">
                          <xsl:value-of select="wiki"/>
                      </xsl:with-param>
                  </xsl:call-template></td>
              <td><xsl:value-of select="birth_date"/> (<xsl:value-of select="birth_year"/>)</td>
              <td><xsl:value-of select="death_date"/> (<xsl:value-of select="death_year"/>)</td>
              <td><xsl:call-template name="Display_Creator-link">
                      <xsl:with-param name="creatorName">
                          <xsl:value-of select="creator"/>
                      </xsl:with-param>
                  </xsl:call-template></td>
              <td><ul>
                  <xsl:for-each select="works/work">
                      <li><xsl:call-template name="Display_ODOK-link">
                          <xsl:with-param name="odokID">
                              <xsl:value-of select="current()"/>
                          </xsl:with-param>
                      </xsl:call-template></li>
                  </xsl:for-each>
              </ul></td>
              <td><xsl:value-of select="changed"/></td>
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
<xsl:template name="Display_Wikidata-link">
    <xsl:param name="wdID" />
    <a><xsl:attribute name="href">
        https://www.wikidata.org/wiki/Special:GoToLinkedPage/svwiki/<xsl:value-of select="$wdID"/></xsl:attribute>
        <xsl:value-of select="$wdID"/>
    </a>
</xsl:template>
<xsl:template name="Display_ODOK-link">
    <xsl:param name="odokID" />
    <a><xsl:attribute name="href">
        http://offentligkonst.se/api/api.php?action=admin&amp;function=info&amp;table=main&amp;format=xsl&amp;id=<xsl:value-of select="$odokID"/></xsl:attribute>
        <xsl:value-of select="$odokID"/>
    </a>
</xsl:template>
<xsl:template name="Display_Creator-link">
    <xsl:param name="creatorName" />
    <a><xsl:attribute name="href">
        http://commons.wikimedia.org/wiki/Creator:<xsl:value-of select="$creatorName"/></xsl:attribute>
        <xsl:value-of select="$creatorName"/>
    </a>
</xsl:template>
</xsl:stylesheet>
