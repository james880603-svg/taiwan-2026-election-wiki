# 2026 縣市首長選舉資料庫

整理 2026-11-28 台灣地方選舉 22 縣市首長候選人、政見、民調與 2022 年結果的中立資料網站。
技術架構參考 Andrej Karpathy 的 「LLM Wiki」構想（idea file）：AI 依 `CLAUDE.md` 的規則維護 Markdown 知識庫，再由腳本產生網站。

- 網站：`https://<你的帳號>.github.io/<repo 名稱>/`
- AI 規則檔：[`CLAUDE.md`](CLAUDE.md)

## 結構

| 層 | 位置 | 說明 |
|---|---|---|
| 原始來源 | `raw/sources.yaml` | 來源登記簿（只追加；不存全文） |
| 知識庫 | `wiki/` | 縣市、候選人、民調、綜合比較頁 |
| 規則 | `CLAUDE.md` | 中立原則、頁面格式、工作流程 |
| 範本 | `templates/` | 新增頁面時複製 |
| 網站 | `docs/` | `build.py` 產生，GitHub Pages 發布 |

## 建置

```bash
pip install -r requirements.txt
python build.py          # 產生 docs/ 並執行檢查
python build.py --lint   # 只檢查
```

## 部署到 GitHub Pages

Settings → Pages → Source 選 **Deploy from a branch**，Branch 選 `main`、資料夾選 `/docs`。

## 封關（11/18 前一定要做）

公職人員選舉罷免法第 53 條：投票日前 10 日起不得發布民調。
1. 2026-11-18 00:00 前執行 `python build.py --no-polls`（或 11/18 當天直接 `python build.py`，會自動隱藏）。
2. 把 `wiki/polls/` 移出 repo 暫存，推上 GitHub。
3. 11/28 16:00 投票結束後放回並重新建置。

## 如何讓 AI 新增一個縣市

對 AI 說：「依 CLAUDE.md 第 7.2 節，把 `wiki/cities/hsinchu-city.md` 升級成完整版。」
AI 會依規則補候選人頁、政見（數量平衡）、民調、2022 結果，執行 `build.py --lint`，並記錄到 `wiki/log.md`。
