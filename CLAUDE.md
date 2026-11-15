# CLAUDE.md — 2026 縣市首長選舉資料庫（Election Wiki）

> 給 AI 的專案說明書。每次開新對話、要新增或修改任何內容之前，**先完整讀完本檔**。
> 本專案的技術邏輯參考 Andrej Karpathy 的「LLM Wiki」模式：由 AI 持續累積、維護一套互相連結的 Markdown 知識庫，再由腳本把它轉成可瀏覽的網站。

---

## 0. 一分鐘看懂這個專案

| 項目 | 內容 |
|---|---|
| 目的 | 整理 2026 年 11 月 28 日台灣地方選舉中 **22 縣市首長** 的候選人、政見、民調與歷屆結果，做成中立、可查證的新聞整理網站 |
| 範圍 | 只做直轄市長與縣（市）長。**不做**議員、鄉鎮市長、村里長、公投（公投只在總覽提一句） |
| 深度 | 六都＝完整版（候選人頁＋政見＋民調＋2022 結果）；其餘 16 縣市＝簡版（號次名單＋待補清單） |
| 網站 | `python build.py` 把 `wiki/` 轉成 `docs/`，GitHub Pages 從 `docs/` 發布 |
| 風格 | 新聞整理風：米白底、黑字、襯線標題、細分隔線、表格為主，**不使用任何政黨代表色** |
| 語言 | 繁體中文（台灣用語） |

---

## 1. 三層架構（對應 Karpathy LLM Wiki）

```
專案根目錄/
├── CLAUDE.md                 ← 第三層：Schema（本檔），規則與流程
├── raw/                      ← 第一層：原始來源（只追加、不改寫）
│   ├── README.md
│   └── sources.yaml          ← 來源登記簿：每筆來源一個 ID（S001…）
├── wiki/                     ← 第二層：AI 維護的知識庫（網站的內容來源）
│   ├── index.md              ← 首頁文字
│   ├── overview.md           ← 全國總覽
│   ├── open-questions.md     ← 待查清單（資料缺口、矛盾、待補頁面）
│   ├── log.md                ← 時間序日誌（只能附加）
│   ├── cities/<city-id>.md   ← 縣市頁（22 個）
│   ├── candidates/<id>.md    ← 候選人頁（目前只有六都主要候選人）
│   ├── polls/<city-id>.yaml  ← 民調資料（只有結構化數字，不寫評論）
│   └── syntheses/<topic>.md  ← 跨縣市比較、閱讀指南等綜合頁
├── templates/                ← 新增頁面時複製用的範本
├── assets/style.css          ← 網站樣式（唯一的 CSS 檔）
├── build.py                  ← 建置腳本：wiki/ → docs/，並執行 lint 檢查
└── docs/                     ← 建置產物（不要手改，一律重新 build）
```

### 1.1 鐵則

1. **`raw/sources.yaml` 只能追加**：新增來源就加一筆新 ID，不改寫、不刪除舊紀錄。若來源內容更新，新增一筆並在 `note` 註明取代哪一筆。
2. **不存新聞全文**：因為 repo 是公開的，`raw/` 只記錄「標題、媒體、日期、網址、我方用自己的話寫的重點」。不可貼上文章段落；必要引文少於 15 字。
3. **`docs/` 不手改**：所有修改都改 `wiki/`、`assets/` 或 `build.py`，再重新執行 `python build.py`。
4. **每一個事實主張都要有來源 ID**：寫成 `[S012]`，build 會自動轉成連到來源頁的上標連結。沒有來源的話就不寫，改記到 `open-questions.md`。
5. 刪除或合併頁面前，先問使用者。

---

## 2. 中立原則（最重要，違反就要修）

這是政治主題，網站必須讓任何立場的讀者都覺得公平。

1. **排列順序**：所有候選人一律依 **中選會號次**（frontmatter 欄位 `ballot`；不可用 `no`，YAML 會把它當成布林值）由小到大排列（縣市頁表格、民調欄位、比較表都一樣）。號次未公布前依登記順序。
2. **同等篇幅**：同一縣市的主要候選人，頁面使用**相同章節**、政見條列**數量相差不超過 1 條**。找不到資料就寫「尚未收錄」，不可只補一方。
3. **只寫候選人自己的主張**：候選人頁的「主要政見」只放本人或其競選團隊提出的內容；**不收錄對手的攻擊、名嘴評論、網友說法**。
4. **第三方評比要整組放**：引用民間團體評比（如社宅政見評比）時，同一縣市的所有受評候選人要一起列出，包括「未回應」者。
5. **不預測勝負**：不寫「看好」「穩贏」「翻盤」等字眼；不從民調推論結果。
6. **中性用詞**：用「主張」「提出」「表示」，不用「狂酸」「嗆」「打臉」等新聞標題用語。
7. **顏色**：政黨標籤一律同一種灰色樣式，不用藍、綠、白、橘等政黨色。
8. **主要候選人的定義**（決定誰有獨立頁面）：政黨推薦，且出現在本站收錄的任一份民調中。其他候選人在縣市頁的名單表中列出號次、政黨與簡歷，不另開頁。這條規則對所有政黨一體適用。
9. **官方資訊以中選會為準**：號次、候選人名單、開票結果，若媒體與中選會不同，以中選會為準，並在 `open-questions.md` 記錄差異。

---

## 3. 民調規則（含法律限制）

### 3.1 收錄標準
- 必須有：發布日期、委託單位、執行單位、調查期間、樣本數、抽樣誤差、調查方法、各候選人支持度。缺項就填 `null`，並在 `note` 說明「原文未載」。
- **政黨、陣營、團體委託的民調也收**，但 `sponsor_type` 要如實標示（媒體／政黨或黨團／民間團體／學術）。讓讀者自己判斷。
- **不收**：AI 模擬、網路聲量、地下賭盤、網路投票、只轉述「差距幾%」卻沒有各自數字的二手報導（後者可記在 `note`）。
- 民調數字**只能寫在 `wiki/polls/*.yaml`**，不可寫在任何 `.md` 的內文裡。這樣才能一鍵隱藏（見 3.2）。`build.py` 會檢查內文是否同時出現「民調」與「%」並發出警告。

### 3.2 選前十天禁止發布民調（公職人員選舉罷免法第 53 條）
- 投票日前 10 日起至投票截止前，任何人不得發布、報導、散布、評論或引述民調。
- 本屆：**2026-11-18 00:00 起至 2026-11-28 16:00（台灣時間）**。
- `build.py` 會依建置時間自動判斷：在這段期間建置時，所有民調表格會被拿掉，改顯示說明文字。
- **在 11/18 00:00 之前必須重新 build 並推上 GitHub**，否則舊版網頁仍會顯示民調。同時建議把 `wiki/polls/` 暫時移出公開 repo（見 README 的「封關」步驟）。
- 封關期間 AI 不得新增、修改、引述任何民調；使用者要求時要提醒此規定。
- 11/28 16:00 投票結束後才可恢復。

---

## 4. 檔案命名

| 類型 | 位置 | 命名 | 範例 |
|---|---|---|---|
| 縣市 | `wiki/cities/` | 英文小寫 kebab-case | `taipei.md`、`new-taipei.md`、`chiayi-city.md` |
| 候選人 | `wiki/candidates/` | 姓名羅馬拼音（以本人常用拼法為準） | `chiang-wan-an.md` |
| 民調 | `wiki/polls/` | 與縣市 id 相同 | `taipei.yaml` |
| 綜合頁 | `wiki/syntheses/` | 主題英文 | `social-housing.md` |
| 來源 | `raw/sources.yaml` | 流水號 `S` + 三位數 | `S015` |

22 縣市 id：`taipei` `new-taipei` `taoyuan` `taichung` `tainan` `kaohsiung` `keelung` `hsinchu-city` `hsinchu-county` `miaoli` `changhua` `nantou` `yunlin` `chiayi-city` `chiayi-county` `pingtung` `yilan` `hualien` `taitung` `penghu` `kinmen` `lienchiang`

---

## 5. 各類頁面格式

所有 `.md` 都以 YAML frontmatter 開頭。`build.py` 讀 frontmatter 產生表格，讀內文產生文章段落。**欄位名稱不可自創**，要新增欄位先改本檔與 `build.py`。

### 5.1 縣市頁 `wiki/cities/<id>.md`（範本：`templates/city.md`）

```yaml
---
type: city
id: taipei
name: 臺北市
tier: 直轄市            # 直轄市 | 縣 | 市
status: full            # full（完整版）| stub（簡版）
updated: 2026-11-15
incumbent: {name: 蔣萬安, party: 國民黨, running: true}   # 不確定就寫 null
candidates:              # 依號次排序
  - {ballot: 1, name: 郭璽, party: 台灣麻將最大黨, bio: 海軍退役上校}
  - {ballot: 3, name: 沈伯洋, party: 民進黨, bio: 立法委員, page: shen-po-yang}
candidates_source: [S004, S005]
history_2022:            # 2022 首長選舉前幾名；只填有來源的數字
  source: [S009]
  rows:
    - {name: 蔣萬安, party: 國民黨, votes: 575590, pct: 42.29, elected: true}
result_2026: null        # 選後填入，格式同 history_2022
---
```
內文固定章節（依序）：`## 選情摘要`、`## 焦點議題`、`## 民調`（只放一行 `{{polls}}`，build 會自動換成表格）、`## 待補`。

### 5.2 候選人頁 `wiki/candidates/<id>.md`（範本：`templates/candidate.md`）

```yaml
---
type: candidate
id: shen-po-yang
name: 沈伯洋
city: taipei
ballot: 3
party: 民進黨
incumbent: false
current_role: 不分區立法委員
updated: 2026-11-15
---
```
內文固定章節（依序，不可增減）：`## 基本資料`、`## 參選歷程`、`## 主要政見`（3～5 條，每條附來源）、`## 第三方評比`、`## 來源與待補`。

### 5.3 民調 `wiki/polls/<city-id>.yaml`（範本：`templates/poll.yaml`）
見範本。`results` 的 key 必須與縣市頁 `candidates` 的 `name` 完全一致。

### 5.4 綜合頁 `wiki/syntheses/<topic>.md`（範本：`templates/synthesis.md`）
跨縣市比較或閱讀指南。frontmatter 需有 `type: synthesis`、`title`、`updated`。比較表一律依「縣市（六都順序：台北、新北、桃園、台中、台南、高雄）→ 號次」排列。

### 5.5 來源 `raw/sources.yaml`
```yaml
- id: S015
  outlet: 遠見《城市學》
  title: 2026六都市長候選人社宅政見評比
  date: 2026-10-22
  url: https://...
  retrieved: 2026-11-15
  kind: 新聞 | 官方 | 民調 | 評比 | 法規
  summary: 用自己的話寫 1～2 句重點（不貼原文）
```

### 5.6 連結寫法
- 站內連結用**一般 Markdown 相對路徑**，連到 `.md`：`[沈伯洋](../candidates/shen-po-yang.md)`。build 會改成 `.html`。（不使用 Obsidian 的 `[[ ]]`，因為 GitHub Pages 看不懂。）
- 來源引用：`[S015]`。

---

## 6. 網頁設計規範（新聞整理風）

- **版面**：最大寬度 960px 置中；頂部報頭（站名＋日期線＋倒數天數）、導覽列、內容、頁尾（資料截至日期＋免責聲明）。
- **字體**：標題用襯線（Noto Serif TC），內文用無襯線（Noto Sans TC），皆有系統字型備援。
- **配色**：底色 `#f7f5f0`、文字 `#1c1c1c`、分隔線 `#d8d2c4`、強調色 `#7a2e1d`（只用於連結與小標籤，不代表任何政黨）。所有顏色定義在 `assets/style.css` 開頭的 CSS 變數，**不要在 HTML 或 Markdown 裡寫行內樣式**。
- **元件**：候選人表格、民調表（數字＋灰色長條）、資訊框（`> [!note]` 會轉成灰框）、來源上標。
- **導覽列固定項目**：首頁｜全國總覽｜六都｜民調｜議題比較｜來源｜關於本站。新增頂層頁面要同時改 `build.py` 的 `NAV`。
- 手機寬度下表格可橫向捲動。

---

## 7. 工作流程

### 7.1 Ingest：收進一則新來源
1. 讀來源（WebFetch 或使用者提供）。
2. 在 `raw/sources.yaml` 末端新增一筆（下一個流水號）。
3. 判斷影響哪些頁面：候選人政見？縣市選情？民調？跨縣市比較？
4. 更新那些頁面，並把 `updated` 改成今天。
5. 若與既有內容矛盾：兩邊都保留，在頁面加 `> [!warning] 資料出入` 說明，並記到 `open-questions.md`。
6. 在 `wiki/log.md` 附加一筆。
7. 執行 `python build.py`，確認沒有 lint 警告。

### 7.2 新增一個縣市的完整版（把 stub 升級成 full）
1. 打開 `wiki/cities/<id>.md`，確認 `candidates` 號次與中選會公告一致。
2. 依第 2 節第 8 條判斷主要候選人；為每位主要候選人複製 `templates/candidate.md` 到 `wiki/candidates/<拼音>.md`，並在縣市頁該候選人加上 `page:`。
3. 為每位主要候選人蒐集 3～5 條政見，**數量平衡**。
4. 蒐集民調（若有），建立 `wiki/polls/<id>.yaml`。
5. 填 `history_2022`（只填有來源的數字）。
6. 寫「選情摘要」「焦點議題」，把 `status` 改成 `full`。
7. 更新 `overview.md` 若有需要；更新 `open-questions.md` 移除已補項目。
8. 記 log、執行 build、檢查網頁。

### 7.3 Query：回答使用者問題
1. 先讀 `wiki/overview.md` 與相關縣市頁，必要時查 `raw/sources.yaml` 的原始網址。
2. 回答附上頁面與來源 ID。
3. 若答案是有保存價值的比較或整理，問使用者是否存成 `wiki/syntheses/` 新頁面，並加進導覽的「議題比較」。

### 7.4 Lint：健康檢查
執行 `python build.py --lint`，腳本會檢查：
- 引用了不存在的來源 ID
- 縣市頁的 `page:` 指向不存在的候選人頁
- 候選人頁缺少固定章節
- 同一縣市主要候選人政見條數相差超過 1
- `.md` 內文出現民調數字
- 民調 `results` 的姓名與縣市頁不符

腳本檢查不到的，由 AI 人工檢查：過時資訊（例如政見已更新）、用詞是否中立、`open-questions.md` 是否有可補的項目。

### 7.5 選後更新（11/28 開票後）
1. 依中選會公告，在各縣市頁填 `result_2026`（格式同 `history_2022`，當選者 `elected: true`）。
2. build 會自動在縣市頁頂端顯示「開票結果」，並在總覽表標示當選人。
3. 12/4 中選會公告當選人名單後再核對一次，於 log 記錄。
4. 民調頁保留作為選前紀錄，標題加註「選前民調（已封存）」。

---

## 8. 建置與部署

```bash
pip install -r requirements.txt   # markdown, pyyaml
python build.py                   # 產生 docs/
python build.py --lint            # 只檢查不產生
python build.py --no-polls        # 強制隱藏民調（封關用）
python build.py --date 2026-11-20 # 模擬某日建置（測試封關邏輯）
```
GitHub Pages 設定：Settings → Pages → Branch: `main`、Folder: `/docs`。

---

## 9. 寫作風格
- 新聞整理口吻：短句、先結論後細節、數字附日期與來源。
- 避免「最新」「目前」等沒有時間錨點的詞，改寫成「截至 2026-11-15」。
- 每頁頂部的 `updated` 必須是最後實際修改日期。

## 10. log.md 格式
```markdown
## [2026-11-15] ingest | 台中市民調 3 筆
- 新增：S050–S052
- 更新：wiki/polls/taichung.yaml、wiki/cities/taichung.md
```
操作類型固定為：`ingest`、`city`、`candidate`、`poll`、`synthesis`、`lint`、`schema`、`build`、`result`。

## 11. 本檔的修改
規則不好用時，提議修改本檔，經使用者同意後更新，並在 log 記一筆 `schema`。
