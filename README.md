# imedic-scp

SCP関連の日本語IME辞書の最小プロトタイプです。IMEに依存しないCSVを編集元として、Microsoft IMEとGoogle 日本語入力にインポートする辞書ファイルの生成を検証します。Python 3.10以上の標準ライブラリだけで動作します。

## 編集元のCSVと列仕様

辞書データの編集元は`data/dictionary.csv`です。文字コードはBOMなしのUTF-8、改行はLF、Unicodeの正規化形式はNFCで保存してください。ヘッダーは次の順序で必ず記載してください。

```csv
reading,term,pos,note
```

| 列 | 内容 |
| --- | --- |
| `reading` | 読み。必須、空白だけの値も不可 |
| `term` | 変換後の表記。必須、空白だけの値も不可 |
| `pos` | IMEに依存しない内部品詞。現在は`proper_noun`のみ |
| `note` | 任意の注記・出典。空欄でも4列目は必要。出力時はコメント列になる |

全フィールドでTAB・CR・LF・NULを禁止します。NFCでない値や`(reading, term, pos)`の完全重複はエラーになります。値の自動修正や空白の除去はしません。カンマや引用符を含む値は通常のCSVルールで引用してください。空行や、列の不足・余分もエラーです。

初期データは「恋昏崎新聞社」「如月工務店」「石榴倶楽部」「ライフラフト」「Imaginanimal」「蒐集院」「無尽月導衆」「五行結社」の8件です。[要注意団体-JP](https://scp-jp.wikidot.com/groups-of-interest-jp)と各団体のハブ、[英語版の要注意団体-JP](https://scp-wiki.wikidot.com/groups-of-interest-jp)で読みを確認しました。カタカナの名称・読みやローマ字表記は、ひらがなに転記しています。読みを推測して追加せず、各行の`note`に出典と読みの確認方法を記載しています。

## 生成とテスト

リポジトリのルートで実行します。

```sh
python scripts/build.py
python -m unittest discover -s tests -v
```

CSVを読み込んで検証し、`Entry`のリストにしてから各exporterに渡します。`scripts/build.py`の各exporterで、内部品詞をIMEの品詞名に対応させます。現在はどちらも`proper_noun`を`固有名詞`に変換します。CSVにIMEの品詞名は記載しません。

| 生成物 | バイト列の仕様 |
| --- | --- |
| `dist/microsoft-ime.txt` | UTF-16LE、BOM `FF FE`、CRLF、先頭行 `!Microsoft IME Dictionary Tool` |
| `dist/google-japanese-input.txt` | UTF-8、BOMなし、LF、ヘッダーなし |

辞書の本文は両方とも`読み<TAB>表記<TAB>品詞<TAB>コメント`の4列です。`note`が空でも、4列目を空欄として出力します。CSVの順序を保ち、最終行にも改行を付けます。Microsoft IME向けのファイルはOSに依存せず同じバイト列になるよう生成し、テストでBOM・文字コード・改行を確認します。

生成物を直接編集しないでください。CSVを編集して再生成します。`dist/`はGit管理の対象外です。

入力の検証に失敗した場合は終了コード1で終了し、既存の生成物は更新しません。そのため、既存ファイルは古い内容のまま残ります。

## インポート手順（Windows）

### Microsoft IME

1. Microsoft IMEの設定から「学習と辞書」→「ユーザー辞書ツール」を開きます。
2. 「ツール」→「テキスト ファイルからの登録」を選びます。
3. `dist/microsoft-ime.txt`を選択し、登録結果と件数を確認します。
4. CSVの読みを入力し、表記が変換候補に表示されることを確認します。

ユーザー辞書ツールの開き方は[Microsoftの説明](https://support.microsoft.com/ja-jp/windows/microsoft-japanese-ime-da40471d-6b91-4042-ae8b-713a96476916)を参照してください。テキストファイルからの登録手順は[富士通の手引書](https://resources.global.fujitsu/software/manual/b1wd-3571/04z000/char-jprapl.pdf)にも記載されています。

### Google 日本語入力

1. Google 日本語入力のメニューから「辞書ツール」を開きます。[公式ヘルプ](https://support.google.com/ime/japanese/answer/166765?hl=ja)に記載のとおり、プロパティの「辞書」→「ユーザ辞書の編集」からも開けます。
2. 「管理」→「新規辞書にインポート」を選びます。
3. `dist/google-japanese-input.txt`と辞書名を指定します。形式はGoogle 日本語入力／Mozc、文字コードはUTF-8を選択します。自動判定も選べます。
4. 登録件数・表記・品詞・コメントと、読みからの変換候補を確認します。

メニュー名や形式選択の有無はバージョンによって異なります。これらの手順も実機で確認してください。

## 形式の根拠と実機検証対象

[Mozcのimporter実装](https://github.com/google/mozc/blob/master/src/dictionary/user_dictionary_importer.cc)で、Microsoft/Mozc形式のタブ区切りと任意の4列目のコメント、`!Microsoft IME`による形式の識別、BOMによるUTF-16の判定を確認しています。

Microsoft IME向けには、日本語を保持して文字コードを明示するためにUTF-16LEとBOMを採用しました。改行はWindows向けにCRLFを選びました。これらの理由はコード内にも記載しています。

現段階ではプロトタイプであり、実際のIMEへのインポートは未検証です。Mozcの実装を確認しても、Microsoft IMEの公式仕様を確認したことにはならず、Google 日本語入力の全バージョンでの動作も保証できません。以下の項目は実機での検証が必要です。

- 現行Microsoft IMEでヘッダーが読み込まれるか、追加のヘッダーが必要か。UTF-16LE・BOM・CRLFが読み込まれるか。
- 両IMEで`固有名詞`として登録されるか。コメント列が空の場合と空でない場合の扱い、インポート件数、読みからの変換。
- Google 日本語入力でUTF-8・BOMなし・LFが読み込まれるか。形式と文字コードの自動判定。
- Windowsと各IMEのバージョンによるメニューや手順の違い。

## 共同編集

IssueやPull Requestによる共同編集を想定しています。名称や読みを追加・訂正する際は、読みを確認できる出典を`note`に添え、CSVを更新してテストを実行してください。実機検証の報告には、WindowsとIMEのバージョン、登録件数、コメントと変換結果を記載してください。
