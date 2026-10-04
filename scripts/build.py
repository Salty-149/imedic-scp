"""編集元のCSVを検証し、標準ライブラリだけで2種類のIME用辞書を生成する。"""

import codecs
import csv
import io
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Entry:
    reading: str
    term: str
    pos: str
    note: str


COLUMNS = ["reading", "term", "pos", "note"]
POSITIONS = {"proper_noun"}
MICROSOFT_POS = {"proper_noun": "固有名詞"}
GOOGLE_POS = {"proper_noun": "固有名詞"}


def load_entries(path: Path) -> list[Entry]:
    # read_text()はCRをLFに変換するため、CRの検出に必要な元の改行が失われる。
    # バイト列として読み込んでからUTF-8でデコードし、元の改行を保つ。
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
        if next(reader, None) != COLUMNS:
            raise ValueError("ヘッダーは reading,term,pos,note の順で必須です（BOMなし）")
        for row in reader:
            location = f"CSV {reader.line_num}行目"
            if len(row) != len(COLUMNS):
                raise ValueError(f"{location}: 4列が必要です")
            for name, value in zip(COLUMNS, row):
                if any(char in value for char in "\t\r\n\0"):
                    raise ValueError(f"{location}: {name}にTAB / CR / LF / NULは使えません")
                if unicodedata.normalize("NFC", value) != value:
                    raise ValueError(f"{location}: {name}がUnicode NFCではありません")
            entry = Entry(*row)
            if not entry.reading.strip() or not entry.term.strip():
                raise ValueError(f"{location}: readingとtermは必須です")
            if entry.pos not in POSITIONS:
                raise ValueError(f"{location}: 不正なpos: {entry.pos!r}")
            key = (entry.reading, entry.term, entry.pos)
            if key in seen:
                raise ValueError(f"{location}: (reading, term, pos)が重複しています")
            seen.add(key)
            entries.append(entry)
    except csv.Error as error:
        raise ValueError(f"CSV {reader.line_num}行目: {error}") from error
    return entries


def export_microsoft(entries: list[Entry]) -> bytes:
    # MozcのGuessIMEType()は、!Microsoft IMEで始まる行をMicrosoft形式と判定する。
    # 非ASCII文字を保持するためにUTF-16LEを使う。BOMを付けることで、Mozcでも
    # 文字コードをUTF-16と判定できる。改行はWindows向けにCRLFを指定する。
    # OSによる改行の変換を避けるため、エンコードしたバイト列を出力する。
    # 現行Microsoft IMEで読み込めるか、追加のヘッダーが必要かは実機で検証する。
    # Mozcでの形式判定は、Microsoftの公式仕様に適合することの保証にはならない。
    lines = ["!Microsoft IME Dictionary Tool"]
    for entry in entries:
        lines.append("\t".join((entry.reading, entry.term, MICROSOFT_POS[entry.pos], entry.note)))
    return codecs.BOM_UTF16_LE + ("\r\n".join(lines) + "\r\n").encode("utf-16-le")


def export_google(entries: list[Entry]) -> bytes:
    lines = []
    for entry in entries:
        lines.append("\t".join((entry.reading, entry.term, GOOGLE_POS[entry.pos], entry.note)))
    return "".join(line + "\n" for line in lines).encode("utf-8")


def build(source: Path, output: Path) -> int:
    entries = load_entries(source)
    # CSVの検証と両形式への変換を終えてから、生成物をファイルに書き込む。
    microsoft = export_microsoft(entries)
    google = export_google(entries)
    output.mkdir(parents=True, exist_ok=True)
    (output / "microsoft-ime.txt").write_bytes(microsoft)
    (output / "google-japanese-input.txt").write_bytes(google)
    return len(entries)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    try:
        count = build(root / "data/dictionary.csv", root / "dist")
    except (ValueError, OSError) as error:
        print(f"生成失敗: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"{count}件をdist/に生成しました")
