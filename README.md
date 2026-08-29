# NSYSU Course API

非官方的國立中山大學課程查詢 API，把 `selcrs.nsysu.edu.tw` 的課程查詢系統轉成
靜態 JSON，含當前學期即時選課人數，以及 111學年下學期～115學年上學期的歷史課程資料。

驗證碼辨識沿用 [nsysu-opendev/NSYSUCourseAPI](https://github.com/nsysu-opendev/NSYSUCourseAPI)
（MIT License）訓練好的 EfficientCapsNet 模型，整串準確率實測 97.3%。

## 資料

| 檔案 | 內容 | 更新頻率 |
|---|---|---|
| `data/current.json` | 目前學期全部課程，含即時限修/點選/選上/餘額 | 每天一次（GitHub Actions），資料沒變化就不動檔案 |
| `data/meta.json` | 目前學期代碼、最後更新時間、課程數 | 跟著 `current.json` 一起更新 |
| `data/diffs/diff_YYYY-MM-DD.txt` | 當天跟前一天比較的異動摘要（新增/消失班次、選課人數變動） | 有變化的那天才會產生 |
| `data/history/{semester}.json` | 各學期完整課程清單（無即時人數，只有最終「修課人數」） | 靜態，不會自動更新 |
| `data/semesters.json` | `data/history/` 底下有哪些學期代碼可查，由新到舊排序 | 每次跑 `convert_to_json.py` 重新產生歷史資料時一起更新 |

**想知道有哪些學期可查，請讀 `data/semesters.json`，不要用 GitHub API 去列
`data/history/` 資料夾**——未登入的 GitHub API 有每小時 60 次的速率限制，
`semesters.json` 純粹是我們自己網域下的一個靜態檔案，沒有這個限制，也少一個
第三方網域依賴。

學期代碼格式是「學年+期」：`1`=上學期、`2`=下學期、`3`=暑期，例如 `1151`＝115學年度上學期。

### 直接取用

Repo 是公開的，可以直接用 raw URL 抓資料，不需要任何驗證（分支是 `master`）：

```
https://raw.githubusercontent.com/dennischu0116-boop/nsysu-course-api/master/data/current.json
https://raw.githubusercontent.com/dennischu0116-boop/nsysu-course-api/master/data/semesters.json
https://raw.githubusercontent.com/dennischu0116-boop/nsysu-course-api/master/data/history/1151.json
```

或是透過 GitHub Pages：

```
https://dennischu0116-boop.github.io/nsysu-course-api/data/current.json
```

### 欄位說明（`current.json` / `history/*.json`）

```jsonc
{
  "semester": "1151",       // 學期代碼
  "changeNote": null,       // 異動說明（例：「異動」「新增」），沒有則為 null
  "multiRequired": false,   // 是否為「多門必修」班次
  "dept": "資工系",
  "courseNo": "CSE104",
  "grade": "1",             // 建議修習年級
  "classType": "不分班",
  "nameZh": "微積分",
  "nameEn": "CALCULUS",
  "credit": "3",
  "compulsory": true,       // 必修 true / 選修 false
  "capacity": 60,           // 限修人數；history 資料沒有即時人數，固定是 null
  "registered": 0,          // 點選人數；history 資料固定是 null
  "enrolled": 63,           // 選上人數（history 資料裡這是「修課人數」欄位）
  "remaining": -3,          // 餘額；history 資料固定是 null
  "teacher": "程正傑",
  "room": "工EC 9032",
  "schedule": { "三": "567" },  // 星期 -> 節次代碼字串
  "english": false,         // 是否為英語授課
  "tags": ["跨領域智慧製造學程", "機器學習與應用微學程"],  // 學程/微學程標記
  "remarks": "《講授類》 / 限本系學生修習"
}
```

`tags` 不是我們自己分類出來的——官網的備註欄裡，每個學程名稱本來就是用獨立的
`<font color="red">` 包起來顯示（其他文字如「限本系學生修習」「※英語授課」
則是純文字），爬蟲只是把這個既有的格式化資訊拆出來變成陣列，`remarks` 則是
拿掉這些 `<font>` 之後剩下的純文字說明。

## 自動更新

`.github/workflows/update.yml` 每天 UTC 01:00（台灣時間早上 09:00）自動執行
`scripts/update_current.py`：偵測目前開放查詢的學期、抓完整課表、跟前一天的
`data/current.json` 比對，只有真的有變化才 commit + push，避免產生一堆空白
異動紀錄。

手動觸發一次：GitHub 網頁上 Actions → Update current semester data → Run workflow，
或用 `gh workflow run update.yml`。

## 本機開發

```bash
pip install -r requirements.txt
python scripts/update_current.py          # 更新 data/current.json
python scripts/convert_to_json.py <csv>   # 從別處產生的 CSV 重新產生 data/history/*.json
```

## 技術重點

- **驗證碼**：用 `scripts/capsnet_model.py` + `scripts/model/EfficientCapsNetDeploy.pth`
  這個預訓練 CapsNet 模型辨識，前處理是灰階 -> 3x3 中值濾波 -> 依寬度平均切 4 份 ->
  resize 28x28。驗證碼裡沒有數字 0，模型輸出類別要 `+1` 校正回 1~9。
- **整學期一次查完**：查詢時 `D1`（系所）故意留空、`DEG_COD=*`，一次拿到全學期
  不分系所的課表，只需要解一次驗證碼，之後的分頁都用同一組已驗證的 token
  （純 GET，見 `scripts/common.py` 的 `query_whole_catalog`）。逐一系所代碼查
  會因為「文學院（全）」「工學院（全）」這類聚合系所代碼跟底下個別系所重複
  列出同一批課，造成資料膨脹。
- **歷年查詢**：網站首頁選單有兩個入口——「當學期課程」和「歷年課程」。
  「歷年課程」的網址是同一支 `qrycrsfrm.asp?HIS=2`，這個模式對「當學期」和
  「過去學期」都能查（下拉選單一路列到 82 學年度上學期），但沒有即時選課人數
  （拿掉點選/選上/餘額，換成一個「修課人數」欄位）。
- **編碼**：這個網站的回應沒有在 HTTP header 宣告 charset，`requests` 的
  `.text` 屬性會誤判編碼導致中文亂碼，一律要用 `r.content.decode("utf-8")`。

## 授權

MIT License，見 [LICENSE](LICENSE)。驗證碼模型沿用
[nsysu-opendev/NSYSUCourseAPI](https://github.com/nsysu-opendev/NSYSUCourseAPI)
（同為 MIT License）。

## 免責聲明

本專案為非官方工具，資料來源為國立中山大學公開課程查詢系統，僅供技術性整理
與個人查詢使用，與校方無關。請勿高頻率請求造成校方系統負擔。
