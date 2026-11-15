---
type: city
id: CITY-ID            # 見 CLAUDE.md 第 4 節的 22 縣市 id
name: 縣市全名
tier: 縣               # 直轄市 | 縣 | 市
status: stub           # 完成完整版後改 full
updated: YYYY-MM-DD
incumbent: null        # {name: , party: , running: true/false}
candidates:            # 依號次排序；欄位名用 ballot（不可用 no）
  - {ballot: 1, name: 姓名, party: 政黨, bio: 簡歷或 null}
  - {ballot: 2, name: 姓名, party: 政黨, bio: 簡歷, page: 拼音-id}   # 主要候選人才加 page
candidates_source: [S004, S005]
history_2022: null     # {source: [Sxxx], rows: [{name, party, votes, pct, elected}]}
result_2026: null      # 選後依中選會公告填入，格式同 history_2022
---

## 選情摘要

- 每點一句，附來源 [Sxxx]。

## 焦點議題

- **議題名**：各候選人主張摘要 [Sxxx]。

## 民調

{{polls}}

## 待補

- 尚未查到的資料。
