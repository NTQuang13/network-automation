import logging, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler, ReadTimeout
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

log = logging.getLogger("netauto")

def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler("logs/netauto.log"), logging.StreamHandler()])

def run_on_device(dev, task, retries=2, **kwargs):
    params = {k: dev[k] for k in ("host", "device_type", "username", "password")}
    if dev.get("secret"):
        params["secret"] = dev["secret"]
    params["timeout"] = int(dev.get("timeout", 20))
    params["session_log"] = f"logs/session_{dev['name']}.log"
    err = "UNKNOWN"
    for attempt in range(1, retries + 1):
        try:
            with ConnectHandler(**params) as conn:
                if not conn.check_enable_mode():
                    conn.enable()
                return {"name": dev["name"], "ok": True,
                        "data": task(conn, dev, **kwargs)}
        except NetmikoAuthenticationException:
            log.error("%s: sai credential", dev["name"])
            return {"name": dev["name"], "ok": False, "error": "AUTH_FAILED"}
        except (NetmikoTimeoutException, ReadTimeout):
            log.warning("%s: timeout (%d/%d)", dev["name"], attempt, retries)
            err = "TIMEOUT"
            time.sleep(2)
        except Exception as e:
            log.exception("%s: %s", dev["name"], e)
            return {"name": dev["name"], "ok": False, "error": str(e)}
    return {"name": dev["name"], "ok": False, "error": err}

def run_parallel(devices, task, workers=8, **kwargs):
    start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(run_on_device, d, task, **kwargs) for d in devices]
        for f in as_completed(futs):
            results.append(f.result())
    elapsed = time.perf_counter() - start
    ok = sum(r["ok"] for r in results)
    log.info("Xong %d/%d thiết bị trong %.1fs", ok, len(devices), elapsed)
    return results, elapsed