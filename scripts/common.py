"""共用的 session / 送出查詢 / 跟隨分頁邏輯。"""
import re, time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from capsnet_solver import solve
from parser import parse_page

BASE = "https://selcrs.nsysu.edu.tw"


def make_session(historical=False):
    """historical=True 用 HIS=2（歷年課程）模式；False 用當學期模式（保留即時
    選課人數：限修/點選/選上/餘額）。"""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    s.verify = False  # 這台校方伺服器的憑證鏈驗證會失敗，純讀取公開資料，可接受
    params = {"HIS": "2", "eng": "0"} if historical else {}
    s.get(f"{BASE}/menu1/qrycrsfrm.asp", params=params, timeout=15)
    qp = {"HIS": "2", "eng": "", "in_eng": "", "IDNO": "", "ITEM": ""} if historical else {}
    r = s.get(f"{BASE}/menu1/qrycourse.asp", params=qp, timeout=15)
    return s, r.content.decode("utf-8", errors="replace")


def detect_current_semester(qrycourse_html):
    m = re.search(r'<select name="?D0"?.*?</select>', qrycourse_html, re.I | re.S)
    if not m:
        raise RuntimeError("could not find D0 dropdown -- site layout may have changed")
    opt = re.search(r'<option value="(\d{4})">', m.group(0))
    if not opt:
        raise RuntimeError("could not parse a semester code out of the D0 dropdown")
    return opt.group(1)


def fetch_captcha_image(s, tmp_path):
    epoch = int(time.time() * 1000)
    r = s.get(f"{BASE}/menu1/validcode.asp", params={"epoch": epoch}, timeout=15)
    with open(tmp_path, "wb") as f:
        f.write(r.content)
    return tmp_path


def submit_whole_catalog(s, semester, valid_code, historical=False, typ="1"):
    data = {
        "D0": semester, "DEG_COD": "*", "D1": "", "D2": "", "CLASS_COD": "",
        "SECT_COD": "", "TYP": typ, "SDG_COD": "", "teacher": "", "crsname": "",
        "T3": "", "WKDAY": "", "SECT": "", "ValidCode": valid_code,
        "HIS": "2" if historical else "", "IDNO": "", "ITEM": "",
        "nowhis": "1" if historical else "",
    }
    r = s.post(f"{BASE}/menu1/dplycourse.asp", params={"eng": ""}, data=data, timeout=20)
    return r.content.decode("utf-8", errors="replace")


def _follow_all_pages(s, html, delay):
    records, pag = parse_page(html)
    all_records = list(records)
    seen_pages = {pag["cur_page"]}
    next_url = pag["next_url"]
    while next_url and pag["cur_page"] < pag["total_pages"] and len(seen_pages) <= pag["total_pages"]:
        time.sleep(delay)
        r2 = s.get(BASE + next_url, timeout=20)
        html2 = r2.content.decode("utf-8", errors="replace")
        records2, pag2 = parse_page(html2)
        if pag2["cur_page"] in seen_pages:
            break
        seen_pages.add(pag2["cur_page"])
        all_records.extend(records2)
        next_url = pag2["next_url"]
        pag = pag2
    return all_records


def query_whole_catalog(s, semester, max_retries, delay, captcha_tmp, historical=False):
    """D1 留空、DEG_COD=* 一次查出整學期不分系所的課表。只需要一次成功的
    驗證碼，之後的分頁都用同一組已驗證的 token（純 GET）。
    Return (records, attempts_used, status)，status 為 'ok'/'empty'/'gave_up'。"""
    for attempt in range(1, max_retries + 1):
        path = fetch_captcha_image(s, captcha_tmp)
        guess = solve(path)
        if guess is None:
            time.sleep(delay)
            continue
        html = submit_whole_catalog(s, semester, guess, historical=historical)
        if "Wrong Validation Code" in html:
            time.sleep(delay)
            continue
        if "找不到相關課程" in html:
            return [], attempt, "empty"
        if len(html) < 500:
            time.sleep(delay)
            continue
        return _follow_all_pages(s, html, delay), attempt, "ok"
    return None, max_retries, "gave_up"
