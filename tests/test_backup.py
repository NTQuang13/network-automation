from netauto.backup import clean

def test_clean_bo_dong_timestamp():
    cfg = "! Command: show running-config\n! Time: Mon Nov 7\nhostname core1\n"
    assert clean(cfg) == ["hostname core1"]
