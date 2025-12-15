from flask import Flask, request, jsonify
from flask_cors import CORS
import feedparser
import os
import google.generativeai as genai
from dotenv import load_dotenv
import urllib.parse
import re
import json

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# カテゴリー別RSSフィード設定
RSS_FEEDS = {
    '政治': 'https://news.yahoo.co.jp/rss/topics/domestic.xml',
    '経済': 'https://news.yahoo.co.jp/rss/topics/business.xml',
    'スポーツ': 'https://news.yahoo.co.jp/rss/topics/sports.xml',
    'テクノロジー': 'https://news.yahoo.co.jp/rss/topics/it.xml',
    'エンターテイメント': 'https://news.yahoo.co.jp/rss/topics/entertainment.xml'
}

# Gemini設定
gemini_model = None

def init_gemini():
    global gemini_model
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key and api_key != 'your_api_key_here':
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel('gemini-flash-latest')
        return True
    return False

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/categories', methods=['GET'])
def get_categories():
    return jsonify(list(RSS_FEEDS.keys()))

@app.route('/api/news', methods=['GET'])
def get_news():
    """ニュース取得API - バッチ処理でAPI効率化"""
    category = request.args.get('category')
    
    if not category or category not in RSS_FEEDS:
        return jsonify({'error': 'Invalid category'}), 400
    
    try:
        # RSSからニュース取得
        entries = fetch_rss_entries(category)
        
        # バッチ処理で要約とタグを生成（1回のAPIコールで全件処理）
        news_list = generate_batch_summaries(entries, category)
        
        return jsonify(news_list)
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

def fetch_rss_entries(category):
    """RSSフィードからエントリを取得"""
    entries = []
    
    # Yahoo!ニュースから取得
    feed = feedparser.parse(RSS_FEEDS[category])
    if not feed.bozo:
        entries.extend(feed.entries)
    
    # 10件未満の場合、Google Newsで補完
    if len(entries) < 10:
        encoded = urllib.parse.quote(category)
        gfeed = feedparser.parse(f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja")
        if not gfeed.bozo:
            existing_links = {e.get('link', '') for e in entries}
            for e in gfeed.entries:
                if len(entries) >= 10:
                    break
                if e.get('link', '') not in existing_links:
                    entries.append(e)
    
    return entries[:10]

def generate_batch_summaries(entries, category):
    """バッチ処理で全ニュースの要約とタグを一度に生成"""
    global gemini_model
    
    # 基本情報を抽出
    news_data = []
    for i, entry in enumerate(entries):
        title = entry.get('title', 'No Title')
        link = entry.get('link', '')
        published = entry.get('published', entry.get('updated', ''))
        rss_summary = re.sub(r'<[^>]+>', '', entry.get('summary', entry.get('description', '')))
        
        news_data.append({
            'index': i,
            'title': title,
            'link': link,
            'published': published,
            'rss_summary': rss_summary[:100] if rss_summary else ''
        })
    
    # Geminiが利用できない場合のフォールバック
    if not gemini_model and not init_gemini():
        return create_fallback_response(news_data, category)
    
    try:
        # バッチプロンプト作成
        titles_text = "\n".join([f"{d['index']}. {d['title']}" for d in news_data])
        
        prompt = f"""あなたはニュース専門家です。以下の{len(news_data)}件のニュースタイトルそれぞれに対して、要約とタグを生成してください。

【重要な指示】
- 各ニュースの要約は40〜60文字程度で、そのニュースが「何について報じているか」を具体的に説明してください
- タイトルをそのまま繰り返すのではなく、読者にとって価値ある情報を提供してください
- タグは各ニュースに1〜3個、内容を表す具体的なキーワードを選んでください

【出力形式】
必ず以下のJSON形式で出力してください。他の文章は一切含めないでください：
[
  {{"index": 0, "summary": "要約文", "tags": ["タグ1", "タグ2"]}},
  {{"index": 1, "summary": "要約文", "tags": ["タグ1", "タグ2", "タグ3"]}},
  ...
]

【カテゴリー】{category}

【ニュースタイトル一覧】
{titles_text}

【JSON出力】"""

        response = gemini_model.generate_content(prompt)
        
        if response and response.text:
            # JSONパース
            result_text = response.text.strip()
            # マークダウンのコードブロックを除去
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            
            try:
                generated = json.loads(result_text)
                return merge_results(news_data, generated, category)
            except json.JSONDecodeError as je:
                print(f"JSON parse error: {je}")
                print(f"Raw response: {result_text[:500]}")
                return create_fallback_response(news_data, category)
        
        return create_fallback_response(news_data, category)
        
    except Exception as e:
        print(f"Gemini batch error: {e}")
        return create_fallback_response(news_data, category)

def merge_results(news_data, generated, category):
    """生成結果をマージ"""
    result = []
    gen_map = {g['index']: g for g in generated if 'index' in g}
    
    for d in news_data:
        idx = d['index']
        if idx in gen_map:
            g = gen_map[idx]
            summary = g.get('summary', f"{d['title']}に関するニュース")
            tags = g.get('tags', [category])
            if not tags:
                tags = [category]
        else:
            summary = f"{d['title']}に関するニュース"
            tags = [category]
        
        result.append({
            'title': d['title'],
            'summary': summary,
            'link': d['link'],
            'tags': tags[:3],
            'published': d['published']
        })
    
    return result

def create_fallback_response(news_data, category):
    """フォールバック用レスポンス生成"""
    result = []
    for d in news_data:
        # RSSサマリがあれば使用、なければタイトルベースの説明
        if d['rss_summary'] and len(d['rss_summary']) > 20:
            summary = d['rss_summary']
        else:
            summary = f"{d['title']}に関する最新ニュース"
        
        result.append({
            'title': d['title'],
            'summary': summary,
            'link': d['link'],
            'tags': [category],
            'published': d['published']
        })
    return result

if __name__ == '__main__':
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key and api_key != 'your_api_key_here':
        print("\n" + "="*60)
        print("✓ Gemini API key configured")
        print("  Note: Free tier limit is 20 requests/day")
        print("  This app uses 1 request per category change")
        print("="*60 + "\n")
        init_gemini()
    else:
        print("\n" + "="*60)
        print("WARNING: GEMINI_API_KEY not configured")
        print("="*60 + "\n")
    
    app.run(debug=True, port=5000)
