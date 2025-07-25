import os
import sys
from openai import OpenAI

# --------------------------------------------------------------------------
# 1. 初期設定と状況認識
# --------------------------------------------------------------------------
api_key = os.environ.get("OPENAI_API_KEY")
# GitHub Actionsが提供するイベント情報を取得
github_event_name = os.environ.get("GITHUB_EVENT_NAME")
triggering_label = os.environ.get("INPUT_TRIGGERING_LABEL") # ワークフローから受け取るラベル名

if not api_key:
    print("エラー: 環境変数 OPENAI_API_KEY が設定されていません。")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# --------------------------------------------------------------------------
# 2. 人格のロード：Logosの憲法を読み込む
# --------------------------------------------------------------------------
try:
    with open("prompts/logos_pm.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
except FileNotFoundError:
    print("エラー: プロンプトファイル prompts/logos_pm.md が見つかりません。")
    sys.exit(1)

# --------------------------------------------------------------------------
# 3. 動的タスク指示書の生成
# --------------------------------------------------------------------------
user_prompt = ""

#【分岐A】"initiate-proposal"ラベルが貼られて呼ばれた場合
if github_event_name == "issues" and triggering_label == 'initiate-proposal':
    issue_title = os.environ.get("ISSUE_TITLE")
    issue_body = os.environ.get("ISSUE_BODY")

    if not issue_title or not issue_body:
        print("エラー: Issueのタイトルまたは本文が取得できませんでした。")
        sys.exit(1)

    user_prompt = f"""
    # タスク指示: 新規案件の初期設計

    あなたは今、新しい案件のキックオフを任されました。
    あなたの思考OSと、以下の案件情報に基づき、「案件初期設計プラン」を作成してください。
    アウトプットには、あなたの署名を必ず含めてください。

    ## 案件情報
    - 案件名: {issue_title}
    - 初期情報: {issue_body}
    """

# (将来的に、他の分岐（issue_commentなど）をここに追加していく)

# --------------------------------------------------------------------------
# 4. API実行と出力
# --------------------------------------------------------------------------
if not user_prompt:
    print("適切なタスクがありません。処理を終了します。")
    sys.exit(0)

print(f"司令塔「Logos」がタスクを開始しました... (Event: {github_event_name}, Label: {triggering_label})")

try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    ai_response = response.choices[0].message.content
    print("Logosによるタスクが完了しました。")
    
    # 結果をGitHub Actionsの出力に設定
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        print(f'comment_body<<EOF', file=f)
        print(ai_response, file=f)
        print('EOF', file=f)

except Exception as e:
    print(f"APIの呼び出し中にエラーが発生しました: {e}")
    sys.exit(1)