import logging, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler
from netmiko.exceptions import (NetmikoTimeoutException,
                                NetmikoAuthenticationException)

log = logging.getLogger("netauto")

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler("logs/netauto.log"),
                  logging.StreamHandler()])

def run_on_device(dev, task, retries=2, **kwargs):
    """Chạy task(conn, dev, **kwargs) trên 1 thiết bị: đăng nhập, vào enable, retry, phân loại lỗi."""
    params = {k: dev[k] for k in
              ("host", "device_type", "username", "password", "secret") if k in dev}
    params["timeout"] = dev.get("timeout", 15)
    err = "UNKNOWN"
    for attempt in range(1, retries + 1):
        try:
            with ConnectHandler(**params) as conn:
                if not conn.check_enable_mode():   # chưa ở '#' thì vào enable
                    conn.enable()
                return {"name": dev["name"], "ok": True,
                        "data": task(conn, dev, **kwargs)}
        except NetmikoAuthenticationException:
            log.error("%s: sai credential hoặc sai enable password", dev["name"])
            return {"name": dev["name"], "ok": False, "error": "AUTH_FAILED"}
        except NetmikoTimeoutException:
            log.warning("%s: timeout (lần %d/%d)", dev["name"], attempt, retries)
            err = "TIMEOUT"
            time.sleep(2)
        except Exception as e:
            log.exception("%s: lỗi %s", dev["name"], e)
            return {"name": dev["name"], "ok": False, "error": str(e)}
    return {"name": dev["name"], "ok": False, "error": err}

def run_parallel(devices, task, workers=10, **kwargs):
    start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(run_on_device, d, task, **kwargs) for d in devices]
        for f in as_completed(futs):
            results.append(f.result())
    elapsed = time.perf_counter() - start
    log.info("Hoàn tất %d thiết bị trong %.1fs", len(devices), elapsed)
    return results, elapsed
