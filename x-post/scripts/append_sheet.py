#!/usr/bin/env python3
"""投稿文を、投稿を管理しているスプレッドシートの C 列（ツイート）に追加する（Google Sheets API）。

使い方:
  python3 append_sheet.py < post.txt              # 1件（標準入力）
  python3 append_sheet.py -f post1.txt post2.txt  # 複数件（ファイルごとに1件、指定した順に下の行へ）
  python3 append_sheet.py --dry-run -f post.txt   # 書き込まずに、追加する行だけ表示する

C 列で最後に文字が入っている行の、次の行から順に書き込む。値はそのまま（RAW）書き込むので、
「=」「+」で始まる文も数式として解釈されない。

設定は x-post/config.json（git には入れない）。config.example.json をコピーして作る。
  spreadsheet_id : スプレッドシートの ID（URL の /d/ と /edit の間）
  sheet_gid      : 追加先のシート（タブ）の gid（URL の #gid= の後ろ）
  credentials    : サービスアカウントの鍵（JSON）のパス
必要なライブラリ: pip install google-auth requests
"""
import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, '..', 'config.json')
API = 'https://sheets.googleapis.com/v4/spreadsheets'


def load_config():
    if not os.path.exists(CONFIG):
        sys.exit(f'設定ファイルがありません: {os.path.normpath(CONFIG)}（config.example.json をコピーして作る）')
    cfg = json.load(open(CONFIG, encoding='utf-8'))
    cfg['credentials'] = os.path.expanduser(cfg['credentials'])
    return cfg


def session(cred_path):
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    creds = service_account.Credentials.from_service_account_file(
        cred_path, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return AuthorizedSession(creds)


def check(res):
    if res.status_code >= 400:
        sys.exit(f'Sheets API のエラー（{res.status_code}）: {res.text}')
    return res.json()


def main():
    args = sys.argv[1:]
    dry = '--dry-run' in args
    args = [a for a in args if a != '--dry-run']
    if args and args[0] == '-f':
        texts = [open(p, encoding='utf-8').read().strip('\n') for p in args[1:]]
    else:
        texts = [sys.stdin.read().strip('\n')]
    texts = [t for t in texts if t.strip()]
    if not texts:
        sys.exit('追加する投稿文がありません')

    cfg = load_config()
    s = session(cfg['credentials'])
    sid = cfg['spreadsheet_id']

    # gid からシート名を引く
    meta = check(s.get(f'{API}/{sid}', params={'fields': 'sheets.properties(sheetId,title)'}))
    titles = {p['properties']['sheetId']: p['properties']['title'] for p in meta['sheets']}
    gid = int(cfg['sheet_gid'])
    if gid not in titles:
        sys.exit(f'gid {gid} のシートが見つかりません（あるシート: {titles}）')
    title = titles[gid]
    quoted = "'" + title.replace("'", "''") + "'"

    # C 列で最後に値が入っている行
    col = check(s.get(f'{API}/{sid}/values/' + urllib.parse.quote(f'{quoted}!C:C')))
    last = len(col.get('values', []))
    start = last + 1
    rng = f'{quoted}!C{start}:C{start + len(texts) - 1}'
    print(f'シート「{title}」の C{start}〜C{start + len(texts) - 1} に {len(texts)}件 追加します')
    if dry:
        return
    check(s.put(f'{API}/{sid}/values/' + urllib.parse.quote(rng),
                params={'valueInputOption': 'RAW'},
                json={'range': rng, 'majorDimension': 'ROWS', 'values': [[t] for t in texts]}))
    print('追加しました')


if __name__ == '__main__':
    main()
