from netauto.compliance import check_rules

def test_cong_khong_dung_vi_pham():
    rules = [{"name": "unused", "type": "interface_unused_shutdown"}]
    intf = [{"interface": "Ethernet5", "status": "notconnect"}]
    assert check_rules(rules, "", intf, "acc1")[0]["status"] == "FAIL"

def test_must_contain_pass():
    rules = [{"name": "ntp", "must_contain": "^ntp server"}]
    assert check_rules(rules, "ntp server 1.1.1.1", [], "acc1")[0]["status"] == "PASS"

def test_must_not_contain_fail():
    rules = [{"name": "telnet", "must_not_contain": "^management telnet"}]
    assert check_rules(rules, "management telnet\n   no shutdown", [], "acc1")[0]["status"] == "FAIL"
