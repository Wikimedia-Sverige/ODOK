<?xml version="1.0" encoding="UTF-8"?>
<!-- add <?xml-stylesheet type="text/html" href="info.xsl"?> to xml just after xml declaration-->
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
      <xsl:if test="callback/head/warning != ''">
         Warning: <xsl:value-of select="callback/head/warning"/><br/>
      </xsl:if>
      <xsl:for-each select="callback/body">
        <hr/>
		<table frame="box">
			<th align="left" colspan="3">
			   ID: <xsl:value-of select="id"/>
			</th>
		<xsl:for-each select="child::*">
  			<xsl:if test="name() != 'id'">
				<tr>
					<td><xsl:value-of select="name()"/></td>
					<td>:</td>
					<td><xsl:value-of select="."/></td>
				</tr>
			</xsl:if>
		</xsl:for-each>
		</table>
      </xsl:for-each>
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
</xsl:stylesheet>
