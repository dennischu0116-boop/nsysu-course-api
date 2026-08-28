import re
from bs4 import BeautifulSoup

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
ROOM_RE = re.compile(r"^(?P<day>[一二三四五六日])?(?P<periods>[0-9A-Fa-f,]*)\((?P<room>.*)\)\s*$")


def parse_page(html):
    """Parse one result page's HTML into (records, pagination_info)."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr", attrs={"bgcolor": ["#C9D1E2", "#ECEFF4"]})

    records = []
    for tr in rows:
        tds = tr.find_all("td", recursive=False)

        def text(td):
            return td.get_text(strip=True)

        if len(tds) >= 25:
            # current-semester format: 異動說明(x2) + 多門必修 + ... + 點選/選上/餘額 + ...
            note_parts = [text(tds[0]), text(tds[1])]
            change_note = " ".join(p for p in note_parts if p)
            multi_required = text(tds[2])
            year, sem = "", ""
            dept, course_cell, grade, class_type, name_cell = tds[3], tds[4], tds[5], tds[6], tds[7]
            credit, term, req_elect, cap = text(tds[8]), text(tds[9]), text(tds[10]), text(tds[11])
            registered, enrolled, balance = text(tds[12]), text(tds[13]), text(tds[14])
            teacher, room_raw = text(tds[15]), text(tds[16])
            weekday_cells = [text(tds[17 + i]) for i in range(7)]
            remarks = tds[24].get_text(separator="\n", strip=True)
        elif len(tds) >= 21:
            # historical (歷年課程, HIS=2) format: no 異動/多門必修, no 點選/選上/餘額,
            # instead the first two cells are 學年/學期
            change_note = ""
            multi_required = ""
            year, sem = text(tds[0]), text(tds[1])
            dept, course_cell, grade, class_type, name_cell = tds[2], tds[3], tds[4], tds[5], tds[6]
            credit, term, req_elect = text(tds[7]), text(tds[8]), text(tds[9])
            # historical mode has no live 限修/點選/餘額; tds[10] is 修課人數 (final headcount)
            cap, registered, balance = "", "", ""
            enrolled = text(tds[10])
            teacher, room_raw = text(tds[11]), text(tds[12])
            weekday_cells = [text(tds[13 + i]) for i in range(7)]
            remarks = tds[20].get_text(separator="\n", strip=True)
        else:
            continue  # not a data row (safety check)

        dept = text(dept)
        course_no_tag = course_cell.find("a")
        course_no = text(course_cell) if course_no_tag is None else course_no_tag.get_text(strip=True)
        grade = text(grade)
        class_type = text(class_type)

        name_link = name_cell.find("a")
        cname = name_link.get_text(strip=True) if name_link else ""
        eng_font = name_cell.find("font")
        ename = eng_font.get_text(strip=True) if eng_font else ""

        weekday_periods = {WEEKDAYS[i]: weekday_cells[i] for i in range(7) if weekday_cells[i]}

        m = ROOM_RE.match(room_raw)
        room = m.group("room").strip() if m else room_raw

        records.append({
            "year": year,
            "sem": sem,
            "change_note": change_note,
            "multi_required": multi_required,
            "dept": dept,
            "course_no": course_no,
            "grade": grade,
            "class_type": class_type,
            "name_zh": cname,
            "name_en": ename,
            "credit": credit,
            "term": term,
            "req_elective": req_elect,
            "capacity": cap,
            "registered": registered,
            "enrolled": enrolled,
            "balance": balance,
            "teacher": teacher,
            "room": room,
            "schedule": weekday_periods,
            "remarks": remarks,
        })

    # pagination: look for "page=N" links and the "Showing X of Y pages" text
    page_links = soup.find_all("a", href=re.compile(r"dplycourse\.asp\?a="))
    next_url = None
    for a in page_links:
        if "Next Page" in a.get_text() or "下一頁" in a.get_text():
            next_url = a["href"]
            break

    footer_text = soup.get_text()
    m = re.search(r"第\s*(\d+)\s*/\s*(\d+)\s*頁", footer_text)
    cur_page, total_pages = (int(m.group(1)), int(m.group(2))) if m else (1, 1)

    return records, {"cur_page": cur_page, "total_pages": total_pages, "next_url": next_url}


if __name__ == "__main__":
    import sys, json
    with open(sys.argv[1] if len(sys.argv) > 1 else "resp_success.html", encoding="utf-8") as f:
        html = f.read()
    records, pag = parse_page(html)
    out = {"count": len(records), "pagination": pag, "first": records[0], "last": records[-1]}
    with open("parser_out.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("wrote parser_out.json")

    soup = BeautifulSoup(html, "html.parser")
    footer_text = soup.get_text()
    idx = footer_text.find("Showing")
    with open("footer_snippet.txt", "w", encoding="utf-8") as f:
        f.write(footer_text[max(0, idx - 100):idx + 100])
