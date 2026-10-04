# imedic-scp

SCP関連の日本語IME辞書です。編集元のCSVからMicrosoft IMEとGoogle 日本語入力向けの辞書ファイルを生成します。生成した辞書の登録は実機で確認済みです。

## 生成とテスト

Python 3.10以上で、リポジトリのルートから実行してください。追加ライブラリは不要です。

```sh
python scripts/build.py
python -m unittest discover -s tests -v
```

| 生成物 | 形式 |
| --- | --- |
| `dist/microsoft-ime.txt` | UTF-16LE、BOM付き、CRLF |
| `dist/google-japanese-input.txt` | UTF-8、BOMなし、LF |

生成物はタブ区切りの「読み・表記・品詞・コメント」です。`dist/`はGit管理の対象外です。生成物を直接編集せず、CSVを編集して再生成してください。検証エラー時は既存の生成物を更新しません。

## CSVの編集

`data/dictionary.csv`をBOMなしのUTF-8、LF改行、Unicode NFCで保存してください。ヘッダーは次の順序で必須です。

```csv
reading,term,pos,note
```

| 列 | 内容 |
| --- | --- |
| `reading` | 読み。必須 |
| `term` | 変換後の表記。必須 |
| `pos` | 内部品詞。現在は`proper_noun`のみ。各IMEでは`固有名詞`に変換 |
| `note` | 任意の注記・出典。空欄でも列は必要。コメントとして出力 |

`reading`と`term`は空白だけの値も不可です。全フィールドでTAB・CR・LF・NULを禁止します。NFCでない値、`(reading, term, pos)`の重複、空行、列数の過不足はエラーになります。値の自動修正や空白の除去はしません。カンマや引用符を含む値はCSVのルールで引用してください。

名称や読みを追加・訂正する際は、読みを確認できる出典を`note`に記載してください。現在の8件はSCP-JPのページと英語版で確認し、カタカナの名称・読みやローマ字表記をひらがなに転記しています。

## インポート手順（Windows）

### Microsoft IME

1. IME設定の「学習と辞書」→「ユーザー辞書ツール」を開きます。
2. 「ツール」→「テキスト ファイルからの登録」で`dist/microsoft-ime.txt`を選びます。

### Google 日本語入力

1. Google 日本語入力のメニューから「辞書ツール」を開きます。
2. 「管理」→「新規辞書にインポート」で`dist/google-japanese-input.txt`と辞書名を指定します。
3. 形式はGoogle 日本語入力／Mozc、文字コードはUTF-8、または自動判定を選びます。

インポート後は登録件数と変換候補を確認してください。メニュー名はバージョンによって異なります。

## 共同編集

IssueやPull Requestで追加・訂正を受け付けます。CSVを更新したら、生成とテストを実行してください。
