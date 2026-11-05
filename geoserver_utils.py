import os
import requests
from geo.Geoserver import Geoserver


def publish_water_layer(tif_native_path, layer_name, param_type='chla', vmin=0.0, vmax=1.0):
    url = os.environ.get('GEOSERVER_URL', 'http://localhost:8080/geoserver')
    username = os.environ.get('GEOSERVER_USERNAME')
    password = os.environ.get('GEOSERVER_PASSWORD')
    if not username or not password:
        raise RuntimeError('Set GEOSERVER_USERNAME and GEOSERVER_PASSWORD environment variables.')

    geo = Geoserver(url, username=username, password=password)
    workspace = 'water_project'

    tif_native_path = os.path.abspath(tif_native_path)
    tif_native_path = tif_native_path.replace("\\", "/")

    if not os.path.exists(tif_native_path):
        raise Exception(f"❌ TIF 文件不存在: {tif_native_path}")

    if geo.get_workspace(workspace) is None:
        geo.create_workspace(workspace=workspace)

    try:
        geo.delete_layer(layer_name, workspace=workspace)
        geo.delete_coveragestore(layer_name, workspace=workspace)
        print("🧹 已清理旧图层")
    except Exception as e:
        pass  # 静默处理即可

    geo.create_coveragestore(
        layer_name=layer_name,
        path=tif_native_path,
        workspace=workspace
    )
    print("✅ TIF 发布成功")

    # =========================
    # ✅ 动态读取色系配置
    # =========================
    step = (vmax - vmin) / 4
    if step <= 0: step = 0.01

    color_palettes = {
        'chla': ['#EDF8E9', '#BAE4B3', '#74C476', '#31A354', '#006D2C'],
        'sd': ['#EFF3FF', '#BDD7E7', '#6BAED6', '#3182BD', '#08519C'],
        'tp': ['#FEEDDE', '#FDBE85', '#FD8D3C', '#E6550D', '#A63603']
    }

    # 按照参数名称匹配，找不到就用彩虹色
    colors = color_palettes.get(param_type.lower(), ['#0000FF', '#00FF00', '#FFFF00', '#FF7F00', '#FF0000'])

    style_name = f"{layer_name}_style"

    sld_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld">
      <NamedLayer>
        <Name>{layer_name}</Name>
        <UserStyle>
          <FeatureTypeStyle>
            <Rule>
              <RasterSymbolizer>
                <ColorMap type="ramp">
                  <ColorMapEntry color="#000000" quantity="-9999.0" opacity="0"/>
                  <ColorMapEntry color="{colors[0]}" quantity="{vmin:.4f}"/>
                  <ColorMapEntry color="{colors[1]}" quantity="{(vmin + step):.4f}"/>
                  <ColorMapEntry color="{colors[2]}" quantity="{(vmin + step * 2):.4f}"/>
                  <ColorMapEntry color="{colors[3]}" quantity="{(vmin + step * 3):.4f}"/>
                  <ColorMapEntry color="{colors[4]}" quantity="{vmax:.4f}"/>
                </ColorMap>
              </RasterSymbolizer>
            </Rule>
          </FeatureTypeStyle>
        </UserStyle>
      </NamedLayer>
    </StyledLayerDescriptor>
    """

    headers = {"Content-type": "application/vnd.ogc.sld+xml"}
    style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}"

    r = requests.put(style_url, data=sld_content.encode('utf-8'),
                     headers=headers, auth=(username, password))

    if r.status_code not in [200, 201]:
        create_url = f"{url}/rest/workspaces/{workspace}/styles?name={style_name}"
        requests.post(create_url, data=sld_content.encode('utf-8'),
                      headers=headers, auth=(username, password))
        print(f"🎨 动态样式已创建 ({vmin:.2f} ~ {vmax:.2f})")
    else:
        print(f"🎨 动态样式已更新 ({vmin:.2f} ~ {vmax:.2f})")

    layer_url = f"{url}/rest/layers/{workspace}:{layer_name}"
    xml = f"<layer><defaultStyle><name>{style_name}</name></defaultStyle></layer>"

    r = requests.put(layer_url, data=xml, headers={"Content-type": "text/xml"}, auth=(username, password))

    if r.status_code in [200, 201]:
        print("✅ 样式绑定成功")
    else:
        print("❌ 样式绑定失败:", r.text)
