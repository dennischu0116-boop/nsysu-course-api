"""
每日更新腳本（給 GitHub Actions 排程用）：抓「目前」學期不分系所的完整課表
（當學期模式，保留即時選課人數），跟 data/current.json 比對，沒有變化就不動
檔案（讓 git 不會產生空白 commit），有變化才更新並記錄異動摘要到
data/diffs/diff_YYYY-MM-DD.txt。

使用方式：
  python scripts/update_current.py
"""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import make_session, detect_current_semester, query_whole_catalog

DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DIR)
DATA_DIR = os.path.join(REPO_ROOT, "data")
CURRENT_PATH = os.path.join(DATA_DIR, "current.json")
META_PATH = os.path.join(DATA_DIR, "meta.json")
DIFF_DIR = os.path.join(DATA_DIR, "diffs")

LIVE_FIELDS = ["capacity", "registered", "enrolled", "remaining"]


def record_to_json(r, semester):
    return {
        "semester": semester,
        "changeNote": r["change_note"] or None,
        "multiRequired": r["multi_required"] == "*",
        "dept": r["dept"],
        "courseNo": r["course_no"],
        "grade": r["grade"],
        "classType": r["class_type"] or None,
        "nameZh": r["name_zh"],
        "nameEn": r["name_en"],
        "credit": r["credit"],
        "compulsory": r["req_elective"] == "必",
        "capacity": int(r["capacity"]) if str(r["capacity"]).isdigit() else None,
        "registered": int(r["registered"]) if str(r["registered"]).isdigit() else None,
        "enrolled": int(r["enrolled"]) if str(r["enrolled"]).lstrip("-").isdigit() else None,
        "remaining": int(r["balance"]) if str(r["balance"]).lstrip("-").isdigit() else None,
        "teacher": r["teacher"],
        "room": r["room"],
        "schedule": r["schedule"],
        "english": "英語授課" in r["remarks"],
        "tags": r.get("tags", []),
        "remarks": r["remarks"].strip() or None,
    }


def section_key(rec):
    return (rec["courseNo"], rec["teacher"], rec["room"], rec["grade"], rec["classType"])


def diff_records(old_list, new_list):
    old_map = {section_key(r): r for r in old_list}
    new_map = {section_key(r): r for r in new_list}
    old_keys, new_keys = set(old_map), set(new_map)

    lines = []
    added, removed = new_keys - old_keys, old_keys - new_keys
    if added:
        lines.append(f"新增 {len(added)} 個班次")
    if removed:
        lines.append(f"消失 {len(removed)} 個班次")

    changed = 0
    detail = []
    for k in old_keys & new_keys:
        o, n = old_map[k], new_map[k]
        deltas = [f"{f} {o.get(f)}→{n.get(f)}" for f in LIVE_FIELDS if o.get(f) != n.get(f)]
        if deltas:
            changed += 1
            if len(detail) < 50:
                detail.append(f"  {k[0]} {k[1]}: " + ", ".join(deltas))
    if changed:
        lines.append(f"選課人數變動 {changed} 個班次")
        lines.extend(detail)

    return bool(added or removed or changed), lines


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    _, qrycourse_html = make_session(historical=False)
    semester = detect_current_semester(qrycourse_html)
    print(f"Detected current semester: {semester}")

    s, _ = make_session(historical=False)
    captcha_tmp = os.path.join(DIR, "_captcha.png")
    records, attempts, status = query_whole_catalog(s, semester, max_retries=8, delay=0.8,
                                                       captcha_tmp=captcha_tmp, historical=False)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    if status != "ok":
        print(f"status={status} attempts={attempts}, aborting without touching data/current.json")
        sys.exit(1 if status == "gave_up" else 0)

    new_data = [record_to_json(r, semester) for r in records]

    old_data = []
    if os.path.exists(CURRENT_PATH):
        with open(CURRENT_PATH, encoding="utf-8") as f:
            old_data = json.load(f)

    changed, diff_lines = diff_records(old_data, new_data)
    if not changed and old_data:
        print(f"No change since last run ({len(new_data)} courses), leaving current.json untouched")
        return

    with open(CURRENT_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, separators=(",", ":"))

    if diff_lines:
        os.makedirs(DIFF_DIR, exist_ok=True)
        with open(os.path.join(DIFF_DIR, f"diff_{now[:10]}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(diff_lines))

    meta = {"semester": semester, "updated": now, "count": len(new_data), "attempts": attempts}
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Updated current.json: semester={semester} courses={len(new_data)} changed={changed}")


if __name__ == "__main__":
    main()
