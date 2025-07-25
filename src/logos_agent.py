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
issue_number = os.environ.get("ISSUE_NUMBER") # Issue番号も取得

# 必須の環境変数が設定されているかチェック
if not all([api_key, github_event_name, triggering_label, issue_title, issue_body, issue_number]):
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
    
    # フューショット（Few-shot）の例を定義する
    few_shot_example = """
    ## ToDoリストの良い例
    - task: "クライアントのIR資料（中期経営計画、統合報告書）を読み込み、事業戦略と課題を構造化してサマリーを作成する"
      assignee: "人間（GPT Proを活用）"
    - task: "競合他社（最低3社）のAI活用に関する公開事例をデスクリサーチし、レポートを作成する"
      assignee: "AXEL-Athena"
    - task: "上記リサーチ結果を基に、クライアントへの初回ヒアリングでぶつけるべき課題仮説を3つ立案する"
      assignee: "AXEL-Logos"
    - task: "社内の関連業界エキスパートのリストアップと、インタビューを打診する"
      assignee: "人間"
    """

    # このタスク専用の、具体的な指示とアウトプット形式を定義する
    user_prompt = f"""
    # 指示: 新規案件の初期設計

    あなたの役割、思考OS、そして指揮下の組織能力に基づき、以下の新規案件の「初期設計プラン」を作成してください。

    ## 思考のステップ
    1.  **標準プロセスの適用:** まず、あなたが持つ「コンサルティング提案の標準プロセス（3サイクル）」を、この案件の全体像として適用し、プロジェクト全体のフェーズを定義してください。
    2.  **現状分析:** 案件情報から、現時点で我々がどのフェーズにいるのかを判断してください。
    3.  **マイルストーンの抽出と設定:** 案件情報に「1週間後に提案」「来週火曜にインタビュー」といった具体的な日付や期限に関する記述があれば、それを正確に抽出し、直近の主要なマイルストーンとして設定してください。もし具体的な日付情報がなければ、「日付未定」として、やるべきことをマイルストーンとして設定してください。
    4.  **ToDoリストの生成:** 現在のフェーズを達成するために必要な、具体的で網羅的なタスクを洗い出し、最適な担当者（人間/AXEL組織の各エージェント）を割り振ってください。ToDoリストの質は、提供されている「良い例」を参考にしてください。

    {few_shot_example}

    ## 案件情報
    - 案件名: {issue_title}
    - 初期情報: {issue_body}

    ## 要求アウトプット形式（重要）
    あなたの思考結果は、以下のキーを持つ単一のJSONオブジェクトとして厳密に出力してください。
    
    ```json
    {{
      "pull_request_title": "（ここに、この案件にふさわしいPull Requestのタイトルを記述する）",
      "pull_request_body": "（ここに、あなたの署名から始まる、人間への報告メッセージをMarkdown形式で記述する）",
      "status_board_content": {{
        "project_name": "（ここに、案件名を記述する）",
        "status": "（ここに、現在のフェーズ名を記述する。例: サイクル1: 課題の発見と仮説構築）",
        "overall_phases": [(ここに、全体のフェーズ案を示す)
        ],
        "current_phase_index": 0,
        "milestones": [
          {{ "date": "（抽出または設定した日付）", "description": "（設定したマイルストーン）" }}
        ],
        "todo_list": [
          {{ "task": "（生成したタスク1）", "assignee": "（割り振った担当者）" }},
          {{ "task": "（生成したタスク2）", "assignee": "（割り振った担当者）" }}
        ],
        "reminders": "（生成したリマインダー）"
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
        max_tokens=4000
    )
    
    # AIからの返答（JSON文字列）をパースしてPythonの辞書オブジェクトに変換
    ai_outputs = json.loads(response.choices[0].message.content)
    
    print("LogosによるJSONレスポンスの生成が完了しました。")
    
    # --- 成果物の組み立て ---
    pr_title = ai_outputs.get("pull_request_title", f"AI Agent Proposal for Issue #{issue_number}")
    pr_body = ai_outputs.get("pull_request_body", "エラー: PR本文を生成できませんでした。")
    status_data = ai_outputs.get("status_board_content", {})

    # project_status.md ファイルの内容を、新しい構造で動的に組み立てる
    status_md = f"# プロジェクト: {status_data.get('project_name', issue_title)}\n\n"
    
    # 全体フェーズと現在地の表示
    status_md += "## プロジェクト・フェーズ\n"
    phases = status_data.get('overall_phases', [])
    current_index = status_data.get('current_phase_index', -1)
    for i, phase in enumerate(phases):
        if i == current_index:
            status_md += f"- **➡️ {phase} (現在地)**\n"
        else:
            status_md += f"- {phase}\n"
            
    status_md += f"\n---\n## 直近のマイルストーン\n"
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
    # API呼び出しなどでエラーが発生した場合
    print(f"処理中にエラーが発生しました: {e}")
    sys.exit(1)