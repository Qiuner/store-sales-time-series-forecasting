import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
ET.register_namespace("a", "http://schemas.openxmlformats.org/drawingml/2006/main")
ET.register_namespace("p", NS["p"])
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
ET.register_namespace("p14", "http://schemas.microsoft.com/office/powerpoint/2010/main")


def patch_presentation_xml(data: bytes) -> bytes:
    root = ET.fromstring(data)
    sld_sz = root.find("p:sldSz", NS)
    if sld_sz is None:
        raise RuntimeError("ppt/presentation.xml missing p:sldSz")

    cx = sld_sz.attrib.get("cx")
    cy = sld_sz.attrib.get("cy")
    kind = sld_sz.attrib.get("type")

    if (cx, cy) == ("12192000", "6858000") and kind == "screen4x3":
        sld_sz.set("type", "wideScreen")

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print("usage: python tools/pptx_wps_patch.py <input.pptx> [output.pptx]")
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) == 3 else src.with_name(f"{src.stem}_wpsfix{src.suffix}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        unpack_dir = tmp / "unpacked"
        unpack_dir.mkdir()

        with zipfile.ZipFile(src) as zf:
            zf.extractall(unpack_dir)

        presentation_path = unpack_dir / "ppt" / "presentation.xml"
        presentation_path.write_bytes(patch_presentation_xml(presentation_path.read_bytes()))

        if dst.exists():
            dst.unlink()
        shutil.make_archive(str(dst.with_suffix("")), "zip", unpack_dir)
        zip_path = dst.with_suffix(".zip")
        zip_path.replace(dst)

    print(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
