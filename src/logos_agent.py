import os
import sys
import json
from openai import OpenAI

# --------------------------------------------------------------------------
# 1. 初期設定と人格ロード
# --------------------------------------------------------------------------

# GitHub Actionsのワークフローから環境変数として情報を受け取る
api_key = os.environ.get("OPENAI_API_KEY")
github_event_name = os.environ.get("GITHUB_EVENT_NAME")
triggering_label = os.environ.get("INPUT_TRIGGERING_LABEL")
issue_title = os.environ.get("ISSUE_TITLE")
issue_body = os.environ.get("ISSUE_BODY")

# 必須の環境変数が設定されているかチェック
if not all([api_key, github_event_name, triggering_label, issue_title, issue_body]):
    print("エラー: 必要な環境変数が不足しています。ワークフローのwith節を確認してください。")
    sys.exit(1)

# OpenAIクライアントを初期化
client = OpenAI(api_key=api_key)

# Logosの人格（憲法）をファイルから読み込む
try:
    with open("prompts/logos_pm.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
except FileNotFoundError:
    print("エラー: プロンプトファイル prompts/logos_pm.md が見つかりません。")
    sys.exit(1)

# --------------------------------------------------------------------------
# 2. 動的タスク指示書の生成
# --------------------------------------------------------------------------

# user_promptを格納する変数を初期化
user_prompt = ""

#【分岐A】"initiate-proposal"ラベルが貼られて呼ばれた場合
if github_event_name == "issues" and triggering_label == 'initiate-proposal':
    
    # このタスク専用の、具体的な指示とアウトプット形式を定義する
    user_prompt = f"""
    # 指示: 新規案件の初期設計

    あなたの役割と思考OSに基づき、以下の新規案件の「初期設計プラン」を作成してください。
    
    ## 案件情報
    - 案件名: {issue_title}
    - 初期情報: {issue_body}

    ## 要求アウトプット形式（重要）
    あなたの思考結果は、以下のキーを持つ単一のJSONオブジェクトとして厳密に出力してください。Markdownなど、他の形式は一切含まないでください。
    
    ```json
    {{
      "pull_request_title": "（ここに、この案件にふさわしいPull Requestのタイトルを記述する。例: feat: 【JR西日本】初期提案設計 by Logos）",
      "pull_request_body": "（ここに、あなたの署名から始まる、人間への報告メッセージ（初期設計プランのサマリーなど）をMarkdown形式で記述する）",
      "status_board_content": {{
        "project_name": "（ここに、案件名を記述する）",
        "status": "計画中",
        "current_phase": "（ここに、あなたが設計したロードマップの最初のフェーズ名を記述する）",
        "milestones": [
          {{
            "date": "日付未定",
            "description": "（ここに、最初の主要なマイルストーンを記述する）"
          }}
        ],
        "todo_list": [
          {{
            "task": "（ここに、あなたが特定した最初に行うべきタスク1を記述する）",
            "assignee": "（このタスクの担当が「人間」か「AI」かを記述する）"
          }},
          {{
            "task": "（ここに、あなたが特定した最初に行うべきタスク2を記述する）",
            "assignee": "（このタスクの担当が「人間」か「AI」かを記述する）"
          }}
        ],
        "reminders": "（ここに、人間へのリマインドや、注意すべき点を記述する）"
      }}
    }}
    ```
    """

# (将来的に、他のイベントやラベルに応じた分岐をここに追加していく)

# --------------------------------------------------------------------------
# 3. API実行と後処理
# --------------------------------------------------------------------------

# 実行すべきタスク指示（user_prompt）が生成された場合のみ、APIを呼び出す
if not user_prompt:
    print("実行すべき適切なタスクがありません。処理を終了します。")
    sys.exit(0)

print(f"司令塔「Logos」がタスクを開始しました... (Event: {github_event_name}, Label: {triggering_label})")

try:
    # OpenAIのAPIを呼び出して、Logosに思考させる
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"}, # モデルにJSONモードで出力するよう指示
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=4000 # 複雑なJSONを生成するために十分なトークン数を確保
    )
    
    # AIからの返答（JSON文字列）をパースしてPythonの辞書オブジェクトに変換
    ai_outputs = json.loads(response.choices[0].message.content)
    
    print("LogosによるJSONレスポンスの生成が完了しました。")
    
    # --- 成果物の組み立て ---
    pr_title = ai_outputs.get("pull_request_title", f"AI Agent Proposal for Issue #{os.environ.get('ISSUE_NUMBER', '')}")
    pr_body = ai_outputs.get("pull_request_body", "エラー: PR本文を生成できませんでした。")
    status_data = ai_outputs.get("status_board_content", {})

    status_md = f"""# プロジェクト: {status_data.get('project_name', issue_title)}

- **ステータス:** {status_data.get('status', 'N/A')}
- **現在のフェーズ:** {status_data.get('current_phase', 'N/A')}

---
## 直近のマイルストーン
"""
    for milestone in status_data.get('milestones', []):
        status_md += f"- [ ] **{milestone.get('date', '日付未定')}:** {milestone.get('description', '')}\n"

    status_md += "\n---\n## ToDoリスト\n"
    for todo in status_data.get('todo_list', []):
        status_md += f"- [ ] **({todo.get('assignee', '未定')})** {todo.get('task', '')}\n"

    status_md += f"\n---\n## 注意・リマインド事項\n{status_data.get('reminders', '特になし')}\n"
    
    # --- 最終的な出力をGitHub Actionsに渡す ---
    final_outputs = {
        "pr_title": pr_title,
        "pr_body": pr_body,
        "status_file_content": status_md
    }
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        print(f"agent_outputs={json.dumps(final_outputs)}", file=f)

except Exception as e:
    print(f"処理中にエラーが発生しました: {e}")
    sys.exit(1)