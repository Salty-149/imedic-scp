"""編集元のCSVを検証し、標準ライブラリだけで2種類のIME用辞書を生成する。"""

import codecs
import csv
import io
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    """辞書CSVの1行分。列の並びはCOLUMNSと一致させる。"""

    reading: str
    term: str
    pos: str
    note: str


COLUMNS = ["reading", "term", "pos", "note"]
FORBIDDEN_CHARS = "\t\r\n\0"  # TAB / CR / LF / NUL

# CSVの内部品詞から各IMEの品詞名への対応表。
# 品詞を追加するときは両方の表に登録する。片方にしかない品詞は
# POSITIONSに含まれないため、CSVの検証でエラーになる。
MICROSOFT_POS = {"proper_noun": "固有名詞"}
GOOGLE_POS = {"proper_noun": "固有名詞"}
POSITIONS = MICROSOFT_POS.keys() & GOOGLE_POS.keys()

MICROSOFT_FILE = "microsoft-ime.txt"
GOOGLE_FILE = "google-japanese-input.txt"


def load_entries(path: Path) -> list[Entry]:
    """CSVを読み込んで検証し、問題があればValueErrorを送出する。"""
    # テキストモードで開くと改行変換でCRが消えて検出できないため、
    # バイト列として読み込んでから自前でデコードする。
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("CSVはUTF-8で保存してください") from error
    if "\r" in text:
        raise ValueError("CSVはLF改行とし、フィールド内でもCRは禁止です")

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    entries = []
    seen = set()
    try:
        # BOM付きのCSVも先頭の列名が一致せずエラーになる。
        if next(reader, None) != COLUMNS:
            raise ValueError(f"ヘッダーは {','.join(COLUMNS)} の順で必須です（BOMなし）")
        for row in reader:
            location = f"CSV {reader.line_num}行目"
            entry = _parse_row(row, location)
            key = (entry.reading, entry.term, entry.pos)  # noteは重複判定に含めない
            if key in seen:
                raise ValueError(f"{location}: (reading, term, pos)が重複しています")
            seen.add(key)
            entries.append(entry)
    except csv.Error as error:
        raise ValueError(f"CSV {reader.line_num}行目: {error}") from error
    return entries


def _parse_row(row: list[str], location: str) -> Entry:
    """1行分の値を検証してEntryに変換する。値の自動修正はしない。"""
    if len(row) != len(COLUMNS):
        raise ValueError(f"{location}: {len(COLUMNS)}列が必要です")
    for name, value in zip(COLUMNS, row):
        if any(char in value for char in FORBIDDEN_CHARS):
            raise ValueError(f"{location}: {name}にTAB / CR / LF / NULは使えません")
        if not unicodedata.is_normalized("NFC", value):
            raise ValueError(f"{location}: {name}がUnicode NFCではありません")
    entry = Entry(*row)
    if not entry.reading.strip() or not entry.term.strip():
        raise ValueError(f"{location}: readingとtermは必須です")
    if entry.pos not in POSITIONS:
        raise ValueError(f"{location}: 不正なpos: {entry.pos!r}")
    return entry


def _format_lines(entries: list[Entry], pos_names: dict[str, str]) -> list[str]:
    """各エントリーを「読み・表記・品詞・コメント」のタブ区切り行にする。"""
    return [
        "\t".join((entry.reading, entry.term, pos_names[entry.pos], entry.note))
        for entry in entries
    ]


def export_microsoft(entries: list[Entry]) -> bytes:
    """Microsoft IME向けにUTF-16LE・BOM付き・CRLFで出力する。"""
    # 先頭行はMicrosoft形式であることを示すヘッダー。
    # Mozcも!Microsoft IMEで始まるヘッダーをMicrosoft形式と判定する。
    # https://github.com/google/mozc/blob/master/src/dictionary/user_dictionary_importer.cc
    lines = ["!Microsoft IME Dictionary Tool", *_format_lines(entries, MICROSOFT_POS)]
    text = "".join(line + "\r\n" for line in lines)  # OSの改行変換に頼らずCRLFを付ける
    return codecs.BOM_UTF16_LE + text.encode("utf-16-le")


def export_google(entries: list[Entry]) -> bytes:
    """Google 日本語入力向けにUTF-8・BOMなし・LFで出力する。"""
    text = "".join(line + "\n" for line in _format_lines(entries, GOOGLE_POS))
    return text.encode("utf-8")


def build(source: Path, output: Path) -> int:
    """CSVから両形式の辞書を生成し、登録件数を返す。"""
    entries = load_entries(source)
    # 検証や変換の途中で失敗したときに既存の生成物を書き換えないよう、
    # 両形式のバイト列をすべて作り終えてからまとめて書き込む。
    microsoft = export_microsoft(entries)
    google = export_google(entries)
    output.mkdir(parents=True, exist_ok=True)
    (output / MICROSOFT_FILE).write_bytes(microsoft)
    (output / GOOGLE_FILE).write_bytes(google)
    return len(entries)


def main() -> int:
    """data/dictionary.csvからdist/に辞書を生成し、終了コードを返す。"""
    root = Path(__file__).resolve().parent.parent  # 実行場所によらずリポジトリ直下を基準にする
    try:
        count = build(root / "data/dictionary.csv", root / "dist")
    except (ValueError, OSError) as error:
        print(f"生成失敗: {error}", file=sys.stderr)
        return 1
    print(f"{count}件をdist/に生成しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
