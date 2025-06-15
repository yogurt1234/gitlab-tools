# タイトル

# 1. はじめに

1. aa
1. bbb
1. dddd


![alt text](image-1.png)

```html sample.html
hoge = hoge foo-bar
```

```python hoge.py
import requests

# コメント
def fetch_data(url: str) -> dict:
    res = requests.get(url)
    return res.json() if res.ok else {}

print(fetch_data("https://api.example.com/data"))
```

> aa
> hoge

> :::note
> Highlights information that users should take into account, even when skimming.
> aaaaaaaaaaa
> bbbbbbb

> :::note:warn
> Optional information to help a user be more successful.

> :::note:alert
> Optional information to help a user be more successful.

```mermaid
flowchart LR
  A[Code Change] --> B(Build)
  B --> C{Success?}
  C -- Yes --> D(Deploy to Staging)
  C -- No --> E[Notify Developers]
  
  D --> F(Run Tests)
  F --> G{Passed?}
  G -- Yes --> H(Deploy)
  G -- No --> I[Alert]
```

```mermaid
sequenceDiagram
  participant ユーザー
  participant ブラウザ
  participant データベース
  
  ユーザー->>+ブラウザ: ログインする
  ブラウザ->>+データベース: 会員情報を照合
  データベース-->>-ブラウザ: 結果
  
  alt 認証成功
      ブラウザ-->>ユーザー: ダッシュボードを表示
  else 認証失敗
      ブラウザ-->>ユーザー: エラーメッセージを返す
  end

```

```mermaid
gantt
    title プロジェクトスケジュール
    dateFormat  YYYY-MM-DD
    section 開発フェーズ
      要件定義     :a1, 2025-03-01, 10d
      設計         :after a1, 15d
    section テストフェーズ
      テスト実施   :2025-04-01, 10d
```



| x   | x   |
| --- | --- |
| x   | x   |

[https://zenn.dev/mizchi/articles/claude-code-orchestrator](https://zenn.dev/mizchi/articles/claude-code-orchestrator)

[https://qiita.com/papi_tokei/items/11877a857a60965a53fc](https://qiita.com/papi_tokei/items/11877a857a60965a53fc)

[https://www.skygroup.jp/tech-blog/article/1261/](https://www.skygroup.jp/tech-blog/article/1261/)

