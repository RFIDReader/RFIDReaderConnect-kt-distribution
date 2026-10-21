#!/usr/bin/env python3
"""Verify the checksum and public package structure of the staged native binary."""
import hashlib
import io
import json
from pathlib import Path
import plistlib
import zipfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "artifact-provenance.json").read_text())
for name, expected in manifest["files"].items():
    path = root / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"Checksum mismatch: {name}"
artifact = root / manifest["artifact"]
with zipfile.ZipFile(artifact) as archive:
    names = archive.namelist()
    assert not any(name.endswith((".swift", ".kt", ".java", ".c")) for name in names), "Implementation source in binary"
    assert all(not name.startswith("/") and ".." not in Path(name).parts for name in names), "Unsafe archive path"
    if manifest["platform"] == "android":
        with zipfile.ZipFile(io.BytesIO(archive.read("classes.jar"))) as classes:
            entries = classes.namelist()
            assert "com/aerouhf/helios_sdk/RFIDReader.class" in entries
            for hidden in ["CommandCipher", "ResponseFrameDecoder", "ScanLifecycle", "messages/Messenger", "messages/AsyncInventoryParser"]:
                assert f"com/aerouhf/helios_sdk/{hidden}.class" not in entries, f"Unprotected class: {hidden}"
        pom = ET.parse(root / manifest["pom"])
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}
        assert pom.findtext("m:version", namespaces=ns) == manifest["version"]
        assert pom.findtext("m:groupId", namespaces=ns) == "com.aerouhf"
        assert pom.findtext("m:artifactId", namespaces=ns) == "helios-sdk"
    else:
        info = plistlib.loads(archive.read("HeliosSDK.xcframework/Info.plist"))
        libraries = info["AvailableLibraries"]
        identifiers = {lib["LibraryIdentifier"] for lib in libraries}
        assert identifiers == {"ios-arm64", "ios-arm64_x86_64-simulator", "macos-arm64_x86_64"}
        for lib in libraries:
            prefix = f"HeliosSDK.xcframework/{lib['LibraryIdentifier']}/{lib['LibraryPath']}/"
            assert any(name.startswith(prefix) and name.endswith(".swiftinterface") for name in names)
print(f"Verified {manifest['platform']} {manifest['version']}: checksums, public API, protected binary structure.")
