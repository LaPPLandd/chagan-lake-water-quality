<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc">

  <NamedLayer>
    <Name>mapping_result</Name>

    <UserStyle>
      <Title>Chlorophyll-a</Title>

      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>

            <ColorMap type="ramp">
  <ColorMapEntry color="#000000" quantity="-9999.0" opacity="0" label="nodata"/>
  
  <ColorMapEntry color="#0000FF" quantity="15.0" label="15" opacity="1"/>
  <ColorMapEntry color="#00FF00" quantity="20.0" label="20"/>
  <ColorMapEntry color="#FFFF00" quantity="25.0" label="25"/>
  <ColorMapEntry color="#FF7F00" quantity="30.0" label="30"/>
  <ColorMapEntry color="#FF0000" quantity="33.0" label="33"/>
</ColorMap>

          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>

    </UserStyle>
  </NamedLayer>

</StyledLayerDescriptor>
