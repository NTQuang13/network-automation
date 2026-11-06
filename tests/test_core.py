from netauto.compliance import parse_interface_blocks
from netauto.backup import _clean
from netauto.report import build_tables
from netauto.rollback import _blocks

def test_parse_interface_blocks():
    cfg = "interface Ethernet1\n   switchport mode trunk\n!\ninterface Ethernet3\n   shutdown\n!\n"
    b = parse_interface_blocks(cfg)
    assert "shutdown" in b["Ethernet3"] and "shutdown" not in b["Ethernet1"]

def test_clean_ignores_header():
    assert _clean("! Command: show running-config\nvlan 10") == ["vlan 10"]

def test_missing_vlan_and_failed_device(tmp_path):
    vf = tmp_path / "v.yaml"; vf.write_text("vlans:\n  - {id: 10, name: A}\n  - {id: 20, name: B}\n")
    collected = [
        {"name": "sw1", "ok": True, "data": {"interfaces": {"Ethernet2": {"linkStatus": "notconnect"}},
                                             "vlans": {"10": {}}}},
        {"name": "sw2", "ok": False, "error": "TIMEOUT"},
    ]
    t = build_tables(collected, str(vf))
    assert t["Missing VLANs"].to_dict("records") == [{"device": "sw1", "missing_vlan": "20"}]
    assert t["Interfaces Down"].iloc[0]["interface"] == "Ethernet2"
    assert t["Device Status"].iloc[1]["status"] == "FAIL"

def test_blocks_detects_removed_vlan():
    cur = "vlan 40\n   name A\n!\nvlan 50\n   name Lab\n!\n"
    want = "vlan 40\n   name A\n!\n"
    assert "vlan 50" in _blocks(cur) and "vlan 50" not in _blocks(want)