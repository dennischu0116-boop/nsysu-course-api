"""One-off / re-runnable conversion: read the historical CSV (produced by
scraper.py) and split it into one JSON file per semester under data/history/."""
import csv, json, os

DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DIR)


def row_to_record(row):
    return {
        "semester": row["semester"],
        "changeNote": row["change_note"] or None,
        "multiRequired": row["multi_required"] == "*",
        "dept": row["dept"],
        "courseNo": row["course_no"],
        "grade": row["grade"],
        "classType": row["class_type"] or None,
        "nameZh": row["name_zh"],
        "nameEn": row["name_en"],
        "credit": row["credit"],
        "compulsory": row["req_elective"] == "必" or row["req_elective"] == "必修",
        "capacity": int(row["capacity"]) if row["capacity"].isdigit() else None,
        "registered": int(row["registered"]) if row["registered"].isdigit() else None,
        "enrolled": int(row["enrolled"]) if row["enrolled"].lstrip("-").isdigit() else None,
        "remaining": int(row["balance"]) if row["balance"].lstrip("-").isdigit() else None,
        "teacher": row["teacher"],
        "room": row["room"],
        "schedule": {d: row[d] for d in ["一", "二", "三", "四", "五", "六", "日"] if row[d]},
        "english": "英語授課" in row["remarks"],
        "remarks": row["remarks"] or None,
    }


def write_semesters_manifest(out_dir, data_dir):
    """data/semesters.json -- sorted (newest first) list of semester codes
    that have a data/history/{semester}.json file. Consumers should read
    this instead of listing the folder via the GitHub API (rate-limited,
    an extra third-party domain to depend on)."""
    semesters = sorted(
        (f[:-5] for f in os.listdir(out_dir) if f.endswith(".json")),
        reverse=True,
    )
    manifest_path = os.path.join(data_dir, "semesters.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(semesters, f, ensure_ascii=False, separators=(",", ":"))
    print(f"semesters manifest -> {manifest_path} ({len(semesters)} semesters)")


def convert(csv_path, out_dir):
    by_semester = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            by_semester.setdefault(row["semester"], []).append(row_to_record(row))

    os.makedirs(out_dir, exist_ok=True)
    for semester, records in by_semester.items():
        out_path = os.path.join(out_dir, f"{semester}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, separators=(",", ":"))
        print(f"{semester}: {len(records)} courses -> {out_path}")

    write_semesters_manifest(out_dir, os.path.dirname(out_dir))


if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "..", "nsysu_scraper", "courses_4years_all_depts.csv")
    convert(csv_path, os.path.join(REPO_ROOT, "data", "history"))
