import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tools/pptx_wps_diagnose.py <pptx_path>")
        return 2

    pptx_path = Path(sys.argv[1])
    with zipfile.ZipFile(pptx_path) as zf:
        presentation_xml = zf.read("ppt/presentation.xml")
        pres_props_xml = zf.read("ppt/presProps.xml")

    root = ET.fromstring(presentation_xml)
    sld_sz = root.find("p:sldSz", NS)
    if sld_sz is None:
        print("presentation.sldSz: missing")
    else:
        print(
            "presentation.sldSz:",
            f'cx={sld_sz.attrib.get("cx")}',
            f'cy={sld_sz.attrib.get("cy")}',
            f'type={sld_sz.attrib.get("type")}',
        )

    props_root = ET.fromstring(pres_props_xml)
    tags = sorted({elem.tag for elem in props_root.iter() if "2010/main" in elem.tag})
    if tags:
        print("presProps office2010 tags:")
        for tag in tags:
            print(tag)
    else:
        print("presProps office2010 tags: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
