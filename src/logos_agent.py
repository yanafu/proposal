import os
import sys
from openai import OpenAI

# --------------------------------------------------------------------------
# 1. 初期設定：環境変数から情報を受け取る
# --------------------------------------------------------------------------
api_key = os.environ.get("OPENAI_API_KEY")
issue_title = os.environ.get("ISSUE_TITLE")
issue_body = os.environ.get("ISSUE_BODY")

if not all([api_key, issue_title, issue_body]):
    print("エラー: 必要な環境変数（OPENAI_API_KEY, ISSUE_TITLE, ISSUE_BODY）が設定されていません。")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# --------------------------------------------------------------------------
# 2. プロンプトの設計：外部ファイルから人格を読み込み、指示を組み立てる
# --------------------------------------------------------------------------
try:
    with open("prompts/logos_pm.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
except FileNotFoundError:
    print("エラー: プロンプトファイル prompts/logos_pm.md が見つかりません。")
    sys.exit(1)

# Logosへの具体的な指示を組み立てる
user_prompt = f"""
以下の新規案件について、あなたが定義された役割に基づき、提案活動の初期設計（ロードマップと最初のアクション提案）を行ってください。

# 案件名
{issue_title}

# 初期情報（営業からの議事録など）
{issue_body}
"""

# --------------------------------------------------------------------------
# 3. APIの実行：Logosに思考させ、結果を受け取る
# --------------------------------------------------------------------------
print(f"司令塔「Logos」が、案件「{issue_title}」の初期設計を開始しました...")

try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7, # 構造化された中にも、ある程度の創造性を許容
        max_tokens=1500  # 提案内容を十分に記述できるトークン数を確保
    )
    ai_response = response.choices[0].message.content
    print("Logosによる初期設計が完了しました。")
    
    # --------------------------------------------------------------------------
    # 4. 結果の出力：後続のステップで使えるように結果を出力する
    # --------------------------------------------------------------------------
    # この特殊な形式で出力すると、GitHub Actionsの次のステップでこの結果を使える
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        print(f'proposal_plan<<EOF', file=f)
        print(f"🤖 **司令塔 Logosより：**\n\n{ai_response}", file=f)
        print('EOF', file=f)

except Exception as e:
    print(f"APIの呼び出し中にエラーが発生しました: {e}")
    sys.exit(1)