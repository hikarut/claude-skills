#!/usr/bin/env python3
"""過去の投稿データ（data/posts.csv）を、投稿を管理しているスプレッドシートから作り直す（Google Sheets API）。

使い方:
  python3 update_posts.py

名前が「ツイートリスト_」で始まるシート（ツイートリスト_2023、ツイートリスト_2024 …）をすべて読み、
本文（ツイート）が入っている行を posts.csv に書き出す。毎回シートの内容で作り直すので、
反応の数値の更新や、シート上での修正・削除もそのまま反映される。

設定（スプレッドシートの ID・サービスアカウントの鍵）は append_sheet.py と同じ x-post/config.json を使う。
"""
import csv
import os
import re
import sys
import urllib.parse

from append_sheet import API, check, load_config, session

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'posts.csv')
SHEET_PREFIX = 'ツイートリスト_'
KEYS = ['date', 'text', 'kind', 'target', 'image', 'repost', 'imp', 'like', 'rt', 'reply',
        'profile', 'link', 'eng', 'eng_rate', 'intent', 'review']

# シートの列名 → posts.csv の列名
COLS = {'ツイート日': 'date', 'ツイート': 'text', '区分': 'kind', 'ターゲット': 'target',
        '画像有無': 'image', '再投稿': 'repost', 'インプレッション数': 'imp', 'いいね数': 'like',
        'リツイート数': 'rt', '返信数': 'reply', 'プロフィールクリック数': 'profile',
        'リンククリック数': 'link', 'エンゲージメント数': 'eng', 'エンゲージメント率': 'eng_rate',
        '備考（メリット・狙い・意図・仮説など）': 'intent', '振り返り': 'review'}


def num(s, rate=False):
    s = (s or '').replace(',', '').replace('%', '').strip()
    if not s or rate:
        return s
    try:
        return str(int(float(s)))
    except ValueError:
        return ''


def norm_date(s):
    s = re.sub(r'\s+', '', s or '')
    return re.sub(r'\((.)\)', r'(\1) ', s).strip()


def main():
    cfg = load_config()
    s = session(cfg['credentials'])
    sid = cfg['spreadsheet_id']
    meta = check(s.get(f'{API}/{sid}', params={'fields': 'sheets.properties(title)'}))
    titles = sorted(p['properties']['title'] for p in meta['sheets']
                    if p['properties']['title'].startswith(SHEET_PREFIX))
    if not titles:
        sys.exit(f'「{SHEET_PREFIX}」で始まるシートが見つかりません')

    rows = []
    for title in titles:
        quoted = "'" + title.replace("'", "''") + "'"
        values = check(s.get(f'{API}/{sid}/values/' + urllib.parse.quote(quoted))).get('values', [])
        if not values:
            continue
        head = [h.strip() for h in values[0]]
        n = 0
        for v in values[1:]:
            x = {h: (v[i] if i < len(v) else '') for i, h in enumerate(head)}
            if not x.get('ツイート', '').strip():
                continue
            rec = {COLS[h]: x.get(h, '') for h in COLS}
            rec['date'] = norm_date(rec['date'])
            for k in ['imp', 'like', 'rt', 'reply', 'profile', 'link', 'eng', 'eng_rate']:
                rec[k] = num(rec[k], rate=(k == 'eng_rate'))
            rows.append({k: rec[k].strip() for k in KEYS})
            n += 1
        print(f'{title}: {n}件')

    rows.sort(key=lambda r: r['date'])
    prev = len(list(csv.DictReader(open(OUT, encoding='utf-8')))) if os.path.exists(OUT) else 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=KEYS)
        w.writeheader()
        w.writerows(rows)
    print(f'合計 {len(rows)}件（前回 {prev}件）→ {os.path.normpath(OUT)}')


if __name__ == '__main__':
    main()
