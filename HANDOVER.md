# 專案交接文件

> 填寫原則：假設接手的人聯絡不到你。凡是需要「問一下原作者」才能完成的事，都代表這份文件還沒寫完。
> 標記 `TODO` 的地方請務必補齊；不適用的段落請寫「不適用」而不要直接刪除，讓接手者知道你確實考慮過。

| 項目 | 內容 |
|---|---|
| 專案名稱 | NSYSU Course API（非官方中山大學課程查詢 API） |
| 交接人 | TODO（GitHub 帳號 `dennischu0116-boop`，目前是唯一維護者） |
| 接手人 | TODO |
| 交接日期 | TODO |
| 文件最後更新 | 2026-08-29 |
| 程式碼位置 | 公開 API：https://github.com/dennischu0116-boop/nsysu-course-api（分支：`master`，唯一分支）<br>本機輔助工具鏈：`C:\Users\123\Desktop\claude\不知道\nsysu_scraper\`（見下方「兩個資料夾的關係」） |

---

## 0. 兩個資料夾的關係（本文件模板沒有的章節，但很重要）

這個專案實際上橫跨兩個資料夾，接手者一定要先搞懂這個分工，不然會覺得資料是憑空冒出來的：

| 資料夾 | 性質 | 用途 |
|---|---|---|
| `nsysu-course-api/`（這份文件所在處） | **公開 Git repo**，唯一對外的東西 | 存放最終的 JSON 資料、每日自動更新的腳本、GitHub Actions 排程。外部使用者只會接觸到這裡。 |
| `nsysu_scraper/`（本機、**不是** Git repo、沒有上傳到任何地方） | 本機開發/除錯用的工具鏈 | 一次性的「抓 8 個學期完整歷史資料」批次工具、驗證碼分類器的訓練與驗證腳本、樣本資料。`nsysu-course-api/scripts/` 裡的 `parser.py`、`capsnet_model.py`、`capsnet_solver.py` 都是從這裡複製過去的**副本**，不是同一份檔案用 symlink 連過去。 |

**這代表的實務含義**：
- 修 bug（例如網站改版、解析邏輯要調整）時，理論上應該兩邊都改，或至少改完 `nsysu_scraper` 那份之後記得**手動複製**到 `nsysu-course-api/scripts/` 再 commit。這是目前最大的維護風險點，見第 8 節技術債。
- 想重新產生全部 8 個學期的歷史資料（例如網站資料被更新、想抓一份新的快照），要在 `nsysu_scraper` 資料夾跑 `scraper.py`，再用 `nsysu-course-api/scripts/convert_to_json.py` 把產出的 CSV 轉成 `data/history/*.json`。日常的「每天更新當學期」則完全在 `nsysu-course-api` repo 裡自動發生，不需要碰 `nsysu_scraper`。
- `nsysu_scraper` 資料夾**沒有備份**（不是 git repo），如果這台電腦壞了，裡面的 297 張手動標記驗證碼樣本、`labels.json`、舊版 kNN 分類器程式碼會全部遺失。這些東西現在都已經不是正式流程在用的（已改用 CapsNet 模型），遺失了也不影響 `nsysu-course-api` 正常運作，但會失去「當初怎麼做的」的紀錄，建議接手者評估是否要把整個 `nsysu_scraper` 資料夾也放進版本控制或至少備份一份。

---

## 1. 專案概觀

**這個系統在做什麼**
把國立中山大學課程查詢系統（`selcrs.nsysu.edu.tw`，一個沒有公開 API、要過圖形驗證碼的老舊 ASP 系統）轉成一個公開、免驗證碼的靜態 JSON API。內容包含「目前學期」的即時選課人數（每天自動更新一次）和 111學年下學期～115學年上學期共 8 個學期的歷史課程資料（靜態，不會自動更新）。驗證碼辨識是直接沿用開源專案 `nsysu-opendev/NSYSUCourseAPI` 訓練好的模型，不是自己重新訓練的。

**使用者是誰**
目前是交接人自己（`dennischu0116-boop`）在用，作為另一個「學程分析」工具（`export_unmatched.py`，目前還接在別的 API `cleargrad-course-api` 上）未來要遷移過來的資料來源。不是對外公開宣傳、不確定有沒有其他真實使用者。TODO：如果之後有其他人開始依賴這個 API，請在這裡補上。

**目前狀態**

| 功能 | 狀態 | 備註 |
|---|---|---|
| 歷史資料（111下~115上，8 個學期） | 已完成 | 靜態，不會自動更新；如需重新整批抓取見第 0 節 |
| 當學期即時選課人數，每日自動更新 | 已完成，運作中 | GitHub Actions 每天 UTC 01:00 自動跑，已實測連續正常運作 |
| 學期清單 manifest（`data/semesters.json`） | 已完成 | 避免消費端依賴有速率限制的 GitHub API |
| 學程/微學程標籤（`tags` 欄位） | 已完成 | 從官網備註欄的 `<font>` 標記結構化拆出來的，不是自行分類 |
| GitHub Pages 靜態網站 | 已完成 | 有一個極簡 `index.html` 首頁 |
| 本機 Windows 排程自動更新 | **已停用** | 曾經設定過，後來改成完全交給 GitHub Actions 跑，本機排程工作還在但是 disabled 狀態，見 `nsysu_scraper/執行說明.md` |
| 自動化測試 | 不存在 | 見第 9 節 |
| 監控 / 告警 | 不存在 | 見第 6、8 節 |

**不包含的範圍**
- 不能選課、退選、查詢個人選課狀態——這個系統完全是唯讀的公開課程資訊爬蟲，不涉及任何帳號登入。
- 不是中山大學官方系統，跟校方無關，資料僅供技術性整理與個人查詢使用。
- 學程/微學程的「比對哪些課屬於哪個學程」的分析邏輯**不在這個 repo 裡**——那是另一個獨立專案（目前還接 `cleargrad-course-api`，未來規劃遷移來吃這個 API 的 `tags` 欄位，但遷移工作本身還沒做）。
- 沒有使用者帳號系統、沒有前端框架、沒有資料庫。

---

## 2. 系統架構

**技術棧**

| 層級 | 技術 | 版本 | 備註 |
|---|---|---|---|
| 語言 / Runtime | Python | CI 用 3.12；本機開發用 3.13 | 兩邊版本不同，目前沒發現相容性問題 |
| 框架 | 無 | — | 純腳本，沒有 web framework |
| 資料庫 | 不適用 | — | 資料就是 JSON 檔案本身，Git 歷史即是唯一的版本記錄 |
| 快取 / 佇列 | 不適用 | — | |
| 前端 | 無框架的純 HTML | — | 只有一個 `index.html` 靜態頁面 |
| 基礎設施 | GitHub Actions（排程執行）+ GitHub Pages（靜態託管） | — | 兩者都是 GitHub 免費方案內 |
| 關鍵套件 | `requests`, `beautifulsoup4`, `numpy`, `pillow`, `torch` | `torch==2.6.0`（**刻意鎖定版本**，見第 8 節） | |

**架構圖（文字版，沒有畫圖）**

```
selcrs.nsysu.edu.tw（校方課程查詢系統，需過圖形驗證碼）
        │  1. 抓驗證碼圖片
        ▼
scripts/capsnet_solver.py（EfficientCapsNet 模型辨識，準確率 97.3%）
        │  2. 驗證碼文字
        ▼
scripts/common.py: query_whole_catalog()
        │  3. D1 留空、DEG_COD=* 送出查詢 → 一次拿到全學期不分系所的課表
        │     （只需一次驗證碼，後續分頁用同一組已驗證 token 純 GET）
        ▼
scripts/parser.py: parse_page()
        │  4. 解析 HTML table，含把備註欄的 <font> 標籤拆成 tags[]
        ▼
scripts/update_current.py                    scripts/convert_to_json.py
   （GitHub Actions 每日觸發）                  （手動執行，重建歷史資料用）
        │  5a. 跟前一天的 data/current.json 比對    │  5b. 從 CSV 轉出
        │      沒變化就不寫檔、不 commit             │
        ▼                                          ▼
data/current.json + data/meta.json           data/history/{semester}.json
data/diffs/diff_YYYY-MM-DD.txt               data/semesters.json
        │
        ▼
GitHub Pages（https://dennischu0116-boop.github.io/nsysu-course-api/）
raw.githubusercontent.com（免驗證直接讀 JSON）
        │
        ▼
外部消費者（目前只有交接人自己规划中的學程分析工具）
```

**外部依賴**

| 服務 | 用途 | 出問題會怎樣 | 文件 / 支援管道 |
|---|---|---|---|
| `selcrs.nsysu.edu.tw` | 唯一的資料來源 | 網站改版（HTML 結構、驗證碼樣式、URL 參數）會直接讓 `parser.py` 或 `common.py` 解析失敗，需要人工排查修正。這是校方內部系統，沒有官方技術支援管道可以問。 | 無官方文件；本 repo 的 README.md 和 `nsysu_scraper` 資料夾裡有大量逆向工程筆記 |
| `nsysu-opendev/NSYSUCourseAPI`（GitHub） | 驗證碼辨識模型（`EfficientCapsNetDeploy.pth`）與其架構程式碼、前處理邏輯的來源 | 如果對方 repo 消失或改架構，**不影響現有運作**——模型檔案已經下載並存放在本 repo 的 `scripts/model/EfficientCapsNetDeploy.pth`，已經是我們自己的副本。只有想要「升級到對方的新版模型」時才需要對方 repo 還存在。 | https://github.com/nsysu-opendev/NSYSUCourseAPI（MIT License） |
| GitHub Actions / GitHub Pages | 排程執行環境、靜態網站託管 | GitHub 全站掛掉就沒有每日更新、API 也讀不到，但這種狀況通常很快恢復，且不是我們能控制的 | https://www.githubstatus.com/ |
| PyPI / `download.pytorch.org` | 安裝 Python 套件（尤其 `torch`） | CI 跑不起來，需要檢查是否套件來源有變動 | 標準 pip 生態 |

---

## 3. 環境建置

從一台全新的機器開始，到本機能跑起來為止的完整步驟。

**前置需求**
- Python 3.10 以上（建議跟 CI 一致用 3.12，避免遇到本機這台機器曾經踩過的 Windows 特有問題）
- Git
- **Windows 使用者注意**：如果裝 `torch` 時遇到 `OSError: [WinError 1114]`（c10.dll 初始化失敗），這是已知在部分 AMD CPU 上的相容性問題，改裝 `pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu` 可解決（`requirements.txt` 已經鎖定這個版本）。Linux（含 GitHub Actions runner）沒有這個問題。

**步驟**
```bash
# 1. 取得程式碼
git clone https://github.com/dennischu0116-boop/nsysu-course-api.git
cd nsysu-course-api

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 設定環境變數
# 不需要，見下方「環境變數清單」

# 4. 初始化資料庫
# 不適用，沒有資料庫

# 5. 啟動
python scripts/update_current.py
```

**驗證是否成功**
指令執行完畢後印出類似
`Updated current.json: semester=1151 courses=2812 changed=True`
的訊息，且 `data/current.json` 檔案存在、`data/meta.json` 裡的 `count` 是一個合理的正整數（目前約 2800 上下）。

**環境變數清單**
不適用——這個專案完全不需要任何環境變數或 API 金鑰。GitHub Actions 的 `git push` 用的是 workflow 內建的 `GITHUB_TOKEN`（自動注入，不需要手動設定任何 secret）。

**常見建置錯誤**

| 錯誤訊息 | 原因 | 解法 |
|---|---|---|
| `OSError: [WinError 1114] ...c10.dll...` | Windows + 特定 CPU（本機是 AMD Ryzen）上 torch 較新版本的相容性問題 | `pip uninstall torch` 後裝 `torch==2.6.0`（`requirements.txt` 已鎖定此版本，正常裝 requirements.txt 不會遇到） |
| 中文欄位變亂碼 | 對這個網站發請求時如果用 `response.text`，`requests` 會誤判編碼成 ISO-8859-1 | 全部程式碼都必須用 `response.content.decode("utf-8")`，不要改用 `.text`（`common.py` 已經這樣寫，別人改的時候要注意別改回去） |
| `SSLError` / 憑證驗證失敗 | 校方伺服器憑證鏈有瑕疵（已知問題，不是我們這邊的錯） | `common.py` 的 session 已經設定 `s.verify = False`，這是刻意的，因為只讀取公開資料 |

---

## 4. 程式碼導覽

**目錄結構**
```
nsysu-course-api/
├── .github/workflows/update.yml   # 每日排程：跑 update_current.py，有變化才 commit+push
├── data/
│   ├── current.json               # 目前學期，含即時選課人數，每天可能更新
│   ├── meta.json                  # 目前學期代碼、最後更新時間、課程數
│   ├── semesters.json             # data/history/ 底下有哪些學期可查（manifest）
│   ├── diffs/diff_YYYY-MM-DD.txt  # 每次資料有變化時的異動摘要，只有變化的那天才有
│   └── history/{semester}.json    # 8 個學期的靜態歷史課程資料
├── scripts/
│   ├── common.py                  # session 建立、送出查詢、跟隨分頁 —— 核心爬蟲邏輯
│   ├── parser.py                  # 把 HTML table 解析成結構化資料，含 tags 拆分
│   ├── capsnet_model.py           # EfficientCapsNet 模型架構定義（沿用自上游專案）
│   ├── capsnet_solver.py          # 用模型辨識驗證碼圖片
│   ├── model/EfficientCapsNetDeploy.pth  # 預訓練模型權重（約 645KB）
│   ├── update_current.py          # 每日更新腳本（GitHub Actions 呼叫這支）
│   └── convert_to_json.py         # 手動執行：把歷史 CSV 轉成 data/history/*.json
├── index.html                      # GitHub Pages 極簡首頁
├── requirements.txt
├── README.md                       # 面向 API 使用者的文件（欄位說明、endpoint）
└── HANDOVER.md                     # 這份文件
```

**進入點**
- 日常自動更新：`.github/workflows/update.yml` 的 cron 觸發 → `python scripts/update_current.py`。這是唯一「正在跑」的進入點。
- 手動重建歷史資料：`python scripts/convert_to_json.py <csv路徑>`，CSV 來源是 `nsysu_scraper/scraper.py` 的輸出（見第 0 節）。

**專案慣例**
- **沒有設定 linter 或 formatter**（沒有 `.flake8` / `pyproject.toml` / `ruff.toml` 之類的檔案）。這是誠實的技術債，見第 8 節。
- 內部 Python dict 的 key 用 `snake_case`（貼近原始 HTML 欄位語意，例如 `course_no`、`req_elective`），輸出到 JSON 時轉成 `camelCase`（例如 `courseNo`、`compulsory`），刻意讓 API 輸出符合一般 JSON API 的慣例。
- 錯誤處理策略偏簡單：驗證碼答錯就重試（最多 8 次），查無資料視為正常情況（回傳空列表），只有真的多次重試失敗才會印出錯誤並跳過，沒有更細緻的例外分類或重試策略。

**核心檔案**

| 檔案 | 為什麼重要 |
|---|---|
| `scripts/common.py` | `query_whole_catalog()` 是整個系統的心臟——D1 留空一次查全學期的技巧就在這裡，改壞了會導致查詢失效或資料重複 |
| `scripts/parser.py` | HTML 解析邏輯，`extract_tags_and_remarks()` 的呼叫順序（先取 tags 再取剩餘文字）不能顛倒 |
| `scripts/update_current.py` | 每日自動更新的完整流程：偵測學期 → 查詢 → 跟舊資料比對 → 決定要不要寫檔 |
| `.github/workflows/update.yml` | 排程設定，改動這個檔案等於改動整個自動化的觸發時間與行為 |
| `scripts/model/EfficientCapsNetDeploy.pth` | 沒有這個檔案，驗證碼辨識完全無法運作，且**這個檔案沒有存在別的地方備份**（只在這個 repo 裡，以及本機 `nsysu_scraper/model/` 有一份副本） |

**危險區域**

| 位置 | 為什麼不要亂改 |
|---|---|
| `common.py` 裡 `D1` 參數留空、`DEG_COD="*"` 的查詢方式 | 這是刻意的設計，不是疏漏。如果改成逐一系所代碼去查（例如想「只查某個系」），要注意系所代碼表裡有「文學院（全）」「工學院（全）」這類聚合代碼，會跟底下個別系所重複列出同一批課，之前就因為這樣讓歷史資料膨脹了近 1.6 萬筆重複列。 |
| `common.py` 裡 `s.verify = False` | 看起來像是關掉安全檢查，但是刻意保留的——這個學校的伺服器憑證鏈本身有瑕疵，跟資料安全無關，只讀公開資料。不要「順手」改成 `True`，改了會直接連不上。 |
| 所有網路請求一律用 `r.content.decode("utf-8")` | 千萬別改回 `response.text`，這個網站沒有在 HTTP header 宣告 charset，`requests` 會誤判編碼，中文會全部變亂碼且不會報錯，很難察覺。 |
| `parser.py` 的 `extract_tags_and_remarks()` | 一定要先呼叫 `find_all("font")` 抽出 tags、`extract()` 移除，最後才對整個 cell 呼叫 `get_text()`；順序顛倒的話 tags 文字會殘留在 remarks 裡。 |
| `requirements.txt` 裡 `torch==2.6.0` 的版本鎖定 | 不要隨手升級到最新版，這台機器實測 `torch==2.13.0` 在 Windows+AMD CPU 上會炸掉（DLL 初始化失敗）。CI（Linux）本身沒有這個問題，但鎖定版本可以確保本機開發環境也能跑。 |

---

## 5. 資料層

**Schema 說明**
不適用傳統資料庫 schema，但有 JSON 欄位結構，完整定義見 [README.md](README.md) 的「欄位說明」章節。摘要：每筆課程記錄有 `semester`、`dept`、`courseNo`、`nameZh`/`nameEn`、`credit`、`compulsory`、`capacity`/`registered`/`enrolled`/`remaining`（即時人數，只有 `current.json` 有真實值，`history/*.json` 固定是 `null`）、`teacher`、`room`、`schedule`（星期 -> 節次字串的 dict）、`tags`（學程標籤陣列）、`remarks`。

**Migration**
不適用，沒有資料庫可以 migrate。如果之後想改變 JSON 的欄位結構，直接修改 `parser.py` / `convert_to_json.py` / `update_current.py` 裡對應的 dict 建構邏輯，然後重新產生所有 `data/*.json` 檔案（沒有自動 migration 機制，是整批重新產生覆蓋舊檔）。

**測試資料**
不適用——沒有本機測試資料集，所有資料都是即時從 `selcrs.nsysu.edu.tw` 抓的。如果想在不打正式網站的情況下測試解析邏輯，`nsysu_scraper/samples/` 底下有 297 張真實驗證碼圖片樣本可以拿來測 `capsnet_solver.py`（跑 `nsysu_scraper/eval_capsnet.py`），但沒有現成的「假課程 HTML」測試資料。

**備份與還原**
- `data/` 底下所有 JSON 檔案的**每一版都在 git commit 歷史裡**，這是唯一的「備份」機制。想找某一天的資料，`git log` 找到那天的 commit 直接 checkout 該版本的 `data/current.json` 即可。
- **沒有** 額外的資料庫備份、沒有排程備份到別的地方。如果 GitHub repo 本身被刪除，資料就真的沒了（除了 `nsysu_scraper/courses_4years_all_depts.csv` 這份本機的歷史資料副本，但那也只在這台電腦上，見第 0 節的風險提示）。

---

## 6. 部署與維運

**環境列表**

| 環境 | 網址 | 用途 | 部署方式 |
|---|---|---|---|
| 正式（唯一環境） | API：https://dennischu0116-boop.github.io/nsysu-course-api/ 或 https://raw.githubusercontent.com/dennischu0116-boop/nsysu-course-api/master/ ；Repo：https://github.com/dennischu0116-boop/nsysu-course-api | 對外提供資料 | `git push` 到 `master` 即自動生效（GitHub Pages 自動重新部署），無需額外部署指令 |
| 本機開發 | localhost（跑腳本用，沒有本機 web server） | 開發、除錯、手動重跑腳本 | 不適用 |

沒有測試環境。這個專案風險低（唯讀爬蟲、資料本身可重新產生），目前判斷不需要獨立測試環境，但如果之後要大改查詢邏輯，建議先用 `--depts` 指定單一系所在本機測試過，不要直接對正式排程改動。

**部署流程**
1. 在本機改好程式碼
2. `git add` + `git commit` + `git push` 到 `master`
3. 沒有審核流程（單人維護的個人專案），push 即生效
4. 如果改到 `.github/workflows/update.yml`，下一次排程觸發（或手動 `gh workflow run update.yml`）就會套用新流程

**Rollback**
`git revert <commit>` 或直接 `git reset --hard <上一個好的 commit>` 後 `git push --force`（單人 repo，force push 風險低，但還是要小心）。因為沒有資料庫，rollback 程式碼跟 rollback 資料是同一件事（`data/*.json` 本身也在 git 版控裡）。

**監控與告警**
不存在。目前完全依賴「有人偶爾去 GitHub 網頁的 Actions 頁籤看一下有沒有紅叉叉」。**這是一個明確的技術債**，見第 8 節。GitHub 本身會在 workflow 失敗時 email 給 repo owner（GitHub 內建行為，不是我們設定的），這是目前唯一的「告警」。

**Log**
- GitHub Actions 的每次執行 log：repo 的 Actions 頁籤，或 `gh run list` / `gh run view --log`。GitHub 預設保留 90 天。
- 本機執行 `refresh_current.py`（`nsysu_scraper` 資料夾裡的舊版，注意跟 `nsysu-course-api/scripts/update_current.py` 是不同檔案）會寫 `nsysu_scraper/refresh_log.txt`，但那是本機排程已停用後的產物，現在沒有東西在寫它。

**常見故障排查**

| 症狀 | 可能原因 | 檢查順序 |
|---|---|---|
| `data/current.json` 好幾天沒更新 | (1) GitHub Actions 排程失敗 (2) 網站改版導致解析失敗 (3) 驗證碼連續 8 次都沒猜對（機率很低但可能） | 1. 看 repo 的 Actions 頁籤有沒有失敗的執行紀錄 2. 手動跑 `gh workflow run update.yml` 看即時 log 3. 本機跑 `python scripts/update_current.py` 直接看錯誤訊息 |
| 資料筆數忽然變成 0 或極少 | 網站可能改了 HTML 結構，`parser.py` 解析不到預期的欄位 | 手動存一份當下的 HTML response，比對 `parser.py` 裡對 `tds[N]` 的欄位假設是否還成立 |
| 驗證碼辨識準確率明顯下降 | 校方換了驗證碼樣式/字型 | 用 `nsysu_scraper/eval_capsnet.py` 對照新樣本測準確率；如果真的下降，需要重新蒐集樣本訓練，或去看上游 `nsysu-opendev/NSYSUCourseAPI` 有沒有更新模型 |
| `data/semesters.json` 沒有包含最新學期 | `convert_to_json.py` 沒有針對新學期重新跑過（這個 manifest 只在手動重建歷史資料時更新，不是每日自動更新的範圍） | 用 `nsysu_scraper/scraper.py` 抓新學期資料後，跑 `convert_to_json.py` 重新產生 |

**定期維護工作**

| 工作 | 頻率 | 做法 |
|---|---|---|
| 檢查 GitHub Actions 有沒有靜默失敗 | 建議每月至少看一次 | 看 Actions 頁籤，或訂閱 GitHub 失敗通知 email |
| 新學期開始時，確認 `data/current.json` 有正確切換學期 | 每學期開始前後 | 看 `data/meta.json` 的 `semester` 欄位 |
| 新學期資料穩定後，考慮跑一次歷史資料重建，把該學期存進 `data/history/` | 每學期結束後 | 見第 0 節「怎麼重新產生歷史資料」 |
| 追蹤上游 `nsysu-opendev/NSYSUCourseAPI` 有沒有模型更新 | 沒有固定頻率，準確率明顯下降時再看 | 手動比對，非自動化 |

---

## 7. 帳號與權限移交

> 逐項確認，全部完成後請雙方簽名。交接完成後，所有 API key 與密碼一律輪替一次。

| 項目 | 服務 | 已移交 | 已輪替 | 備註 |
|---|---|---|---|---|
| 雲端主機 | 不適用 | — | — | 沒有自己的伺服器，全部靠 GitHub 免費方案 |
| 網域 / DNS | 不適用 | — | — | 用 GitHub Pages 預設網域（`dennischu0116-boop.github.io`），沒有自訂網域 |
| SSL 憑證 | 不適用 | — | — | GitHub Pages 自動處理 |
| Repo 權限 | GitHub（`dennischu0116-boop/nsysu-course-api`） | ☐ | — | 需要把接手人加為 collaborator，或直接 transfer ownership；目前只有 `dennischu0116-boop` 一人有權限 |
| CI/CD | GitHub Actions（用同一個 repo 權限） | ☐ | — | 沒有獨立的 CI 帳號，跟著 repo 權限走 |
| 資料庫帳號 | 不適用 | — | — | 沒有資料庫 |
| 第三方 API key | 不適用 | — | — | **這個專案完全沒有使用任何第三方 API key**，值得特別註記，因為大部分交接文件這裡都會有東西要輪替 |
| 監控 / 告警 | 不適用 | — | — | 沒有設定任何監控服務 |
| 錯誤追蹤 | 不適用 | — | — | 沒有 Sentry 之類的服務 |

---

## 8. 已知問題與技術債

> 誠實列出來，價值遠高於粉飾。

**已知 Bug**

| 描述 | 影響範圍 | 重現方式 | 暫時解法 |
|---|---|---|---|
| 每日 diff 摘要（`data/diffs/diff_*.txt`）的「新增/消失班次」計數有時會偏高，即使實際上只是同一批課的資料略有調整 | 只影響 diff 摘要的可讀性，**不影響 `current.json` 本身的正確性**（那永遠是完整覆蓋、絕對正確的） | 在真實的加退選期間執行兩次 `update_current.py`，比對 diff 檔案內容 | 目前用 `(course_no, teacher, room, grade, class_type)` 當作班次的識別 key，如果這幾個欄位剛好有變動（例如授課教師異動），會被誤判成「舊班次消失+新班次新增」而不是「同一班次的欄位變更」。可以接受但不完美。 |
| 驗證碼連續 8 次都答錯導致該次查詢失敗 | 機率很低（單次成功率 97.3%，連續 8 次都錯的機率約 0.0000002%，但仍可能因為網路問題等其他原因觸發） | 無法穩定重現 | `update_current.py` 遇到這狀況會直接結束、不動 `current.json`，下一次排程（隔天）會再試一次；也可以手動立即重跑 |

**技術債**

| 問題 | 為什麼會這樣 | 建議處理方式 | 急迫性 |
|---|---|---|---|
| `nsysu-course-api/scripts/` 裡的 `parser.py`、`capsnet_model.py`、`capsnet_solver.py` 是從 `nsysu_scraper/` **手動複製**過來的，兩邊會失去同步 | 開發時先在 `nsysu_scraper` 本機工具鏈驗證邏輯，確認可行後才複製進正式 repo，圖方便沒有做成單一來源 | 考慮把 `nsysu_scraper` 也整個放進版控（哪怕是私有 repo），或至少寫一個同步腳本，或乾脆讓 `nsysu-course-api` 成為唯一開發位置 | 中——目前兩邊還是同步的，但每次改動都要記得手動複製，容易漏 |
| 沒有任何自動化測試 | 專案一開始就是探索性質，寫得快，沒有補測試 | 至少針對 `parser.py` 的 HTML 解析寫幾個用真實樣本 HTML 的單元測試，避免網站小改版就整個解析失效卻沒人發現 | 中 |
| 沒有監控/告警，資料停止更新不會有人主動被通知（除了 GitHub 內建的 workflow 失敗 email） | 個人專案，一開始沒有這個需求 | 可以考慮在 workflow 失敗時額外發一個 Discord/Slack webhook 通知（`nsysu-opendev/NSYSUCourseAPI` 的 `parse_info.py` 裡就有這種 webhook 通知的參考做法） | 低~中 |
| 本機 `nsysu_scraper` 資料夾裡還留著已經停用的舊版 kNN 驗證碼分類器（`captcha_solver.py`、`pipeline.py`、`collect_samples.py`、`build_label_sheets.py`、297 張手動標記樣本）| 從 kNN 分類器（55.6% 準確率）升級到 CapsNet 模型（97.3%）後這些就沒用了，但沒有清掉 | 可以整理成一份「早期做法存檔」文件後刪除，或就放著當歷史紀錄，不影響正式運作 | 低 |
| 本機 Windows 工作排程器裡還留著一個 disabled 狀態的排程工作（`NSYSU Course Refresh`） | 從本機排程改成 GitHub Actions 排程時，選擇停用而不是刪除 | 如果確定不會再用本機排程，可以直接 `schtasks /delete` 徹底移除，減少「這台電腦上到底還有什麼東西在跑」的認知負擔 | 低 |
| `torch==2.6.0` 版本鎖死，之後 CVE 修復或新功能都吃不到 | Windows+AMD 相容性問題的權宜之計 | 定期（例如每半年）測試看看新版 torch 在本機是否修好了這個問題，修好了再解除鎖定 | 低 |

**Workaround**
- `requirements.txt` 裡 `torch==2.6.0` 的鎖定：純粹是本機 Windows+AMD 環境的相容性 workaround，CI（Linux）其實不受影響，但為了本機開發體驗一致還是鎖了。
- `common.py` 裡 `s.verify = False`：不是「圖方便關掉安全檢查」，是校方伺服器憑證鏈本身有缺陷（`Missing Subject Key Identifier`）的必要 workaround，只用於讀取這一個公開網站，不涉及任何帳密傳輸。

---

## 9. 測試

**怎麼跑**
不適用——沒有自動化測試套件。

**涵蓋範圍**
完全沒有自動化測試涵蓋。所有驗證都是這次開發過程中手動進行的（例如拿 297 張真實驗證碼樣本手動核對 `eval_capsnet.py` 的準確率、手動比對官網「共 X 筆」的數字跟爬蟲結果是否一致）。

**手動驗收清單**

| 檢查項目 | 預期結果 |
|---|---|
| `curl https://raw.githubusercontent.com/dennischu0116-boop/nsysu-course-api/master/data/current.json` | 回傳合法 JSON，是一個非空的陣列 |
| `curl https://raw.githubusercontent.com/dennischu0116-boop/nsysu-course-api/master/data/semesters.json` | 回傳一個學期代碼字串陣列，第一個是目前最新學期 |
| `curl https://dennischu0116-boop.github.io/nsysu-course-api/` | 回傳 200，看到極簡首頁 |
| `gh workflow run update.yml` 後等待完成 | 執行成功（綠勾），若資料有變化會看到新的 commit 出現在 repo |
| 本機執行 `python nsysu_scraper/eval_capsnet.py` | 印出整串準確率，應該在 95% 以上（目前實測 97.3%），明顯偏低代表驗證碼樣式可能變了 |

---

## 10. 聯絡人

| 角色 | 姓名 | 聯絡方式 | 負責什麼 |
|---|---|---|---|
| 原開發者 / 目前唯一維護者 | TODO | dennischu0116@gmail.com（GitHub: `dennischu0116-boop`） | 全部 |
| PM / 客戶 / 業務窗口 | 不適用 | | 個人專案，沒有這些角色 |
| 外部廠商支援 | 不適用 | | |

**相關文件位置**
- [README.md](README.md) —— 面向 API 使用者的文件，含完整欄位說明與 endpoint
- `nsysu_scraper/執行說明.md`（本機資料夾內）—— 本機排程/工具鏈的操作說明（含現已停用的 Windows 排程細節）
- 上游依賴：https://github.com/nsysu-opendev/NSYSUCourseAPI（驗證碼模型來源）
- 這整個專案是透過與 Claude 的對話逐步開發出來的，沒有另外的需求文件或設計稿——這份 HANDOVER.md 加上 README.md 就是最完整的書面記錄。

---

## 11. 決策紀錄

> 這一節最容易被略過，卻是接手者最需要的。沒有脈絡，他會把你刻意的取捨當成錯誤重寫一遍。

| 決策 | 當時的理由 | 考慮過但沒採用的方案 | 什麼情況下該重新評估 |
|---|---|---|---|
| 查詢時 `D1`（系所）留空、`DEG_COD="*"`，一次拿全學期不分系所的資料 | 逐一系所代碼查詢會因為「文學院（全）」「工學院（全）」這類聚合代碼跟底下個別系所重複列出同一批課，導致資料膨脹（實測歷史資料因此多了近 1.6 萬筆重複列）；而且整批查只需要解一次驗證碼，比逐系所查（190 次）快非常多、對校方伺服器也更友善 | 逐一系所代碼查詢（最初的實作方式，後來發現重複問題才改掉） | 如果校方系統改版導致「不指定系所」的查詢方式失效，才需要退回逐系所查詢，並自行處理去重 |
| 驗證碼辨識改用 `nsysu-opendev/NSYSUCourseAPI` 的預訓練 EfficientCapsNet 模型，捨棄自行訓練的 kNN 分類器 | 自製 kNN 分類器（用 297 張手動標記樣本、shift-tolerant 最近鄰比對）整串準確率只有 55.6%；對方預訓練模型實測 97.3%，且是同一個驗證碼系統，直接適用 | 通用 OCR（Tesseract，實測只有 8%，這個驗證碼字體對它太難）；自己收集更多樣本重新訓練 kNN（邊際效益很小，98 張→297 張只從 50% 提升到 55.6%） | 如果上游專案的模型不再更新維護、或校方換了完全不同的驗證碼樣式，需要重新評估 |
| 歷史學期用 `HIS=2`（歷年模式）查詢，當學期用 `HIS=''`（當學期模式）查詢，兩套邏輯並存 | `HIS=2` 可以查任何學期（下拉選單一路列到 82 學年度上學期）但沒有即時選課人數；`HIS=''` 有即時人數但只能查目前開放的學期。兩者互補，各取所長 | 統一都用其中一種模式（會犧牲歷史資料的可得性，或犧牲當學期的即時人數） | 不太需要重新評估，除非校方把其中一種模式整個下架 |
| 每日更新腳本會跟前一天資料比對，沒有實質變化就不寫檔、不 commit | 避免每天產生大量空白 commit 讓 git history 難以閱讀，也讓 `data/diffs/` 底下的異動記錄真的有意義（只在有變化的日子才存在） | 每天都無條件覆蓋+commit（做法更簡單，但 git history 會很難用，且沒辦法一眼看出「哪幾天有真的異動」） | 如果之後想要「即使沒變化也要有每日快照」的需求（例如做時間序列分析），需要改成無條件寫入，可能要另外設計儲存方式（例如每天一個檔案而非覆蓋同一個檔案） |
| 不用資料庫，純用 JSON 檔案 + Git 版控當「儲存系統」 | 資料量小（8 個學期＋當學期，每學期約 2600~2800 筆，總計 JSON 檔案大小約 10MB 出頭）、更新頻率低（一天一次），GitHub Pages 免費靜態託管完全夠用，也不用管資料庫維運 | 用真正的資料庫（Postgres/SQLite）+ 自己架 API server | 如果資料量或查詢複雜度大幅增加（例如要做全文搜尋、複雜篩選），或需要比「整批下載 JSON」更精細的查詢介面時，才需要重新評估 |
| `tags` 欄位是從官網備註欄的 `<font>` HTML 標籤結構化拆出來的，不是自己判斷分類 | 官網課程查詢頁面本身就用 `<font color="red">` 把每個學程/微學程名稱各自包起來顯示（其他備註文字如「限本系學生修習」「※英語授課」則是純文字），這是既有的、可靠的結構化資訊來源，比自己寫規則判斷「這句話是不是學程名稱」準確且省事得多 | 用關鍵字比對或規則判斷 remarks 文字裡哪些片段是學程名稱 | 如果校方改版拿掉這個 `<font>` 標記方式，`tags` 就會全部變空，需要改用其他判斷方式（屆時要重新評估） |

---

## 12. 交接進度追蹤

| 階段 | 內容 | 完成日 | 確認人 |
|---|---|---|---|
| 1 | 文件交付與閱讀 | | |
| 2 | 架構 walkthrough 會議 | | |
| 3 | 接手人獨立完成環境建置 | | |
| 4 | 接手人獨立完成一次「修 bug → 測試 → 部署」 | | |
| 5 | 帳號權限全部移交並輪替 | | |
| 6 | 正式交接，緩衝支援期開始 | | |

**接手人回饋**
TODO：接手過程中卡住的地方記在這裡，並回頭補進上面對應的章節。這是驗證文件品質最有效的方式。
