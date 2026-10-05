"""scripts/build.pyのCSV検証と辞書出力のテスト。"""

import codecs
import csv
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build import (
    COLUMNS,
    GOOGLE_FILE,
    MICROSOFT_FILE,
    Entry,
    build,
    export_google,
    export_microsoft,
    load_entries,
)


ROOT = Path(__file__).resolve().parent.parent


class DictionaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "dictionary.csv"
        self.row = ["きさらぎこうむてん", "如月工務店", "proper_noun", ""]
        self.entries = [Entry(*self.row), Entry("よみ", "表記", "proper_noun", "注記,引用")]

    def replaced_row(self, index, value):
        """self.rowのindex列だけをvalueに置き換えた行を返す。"""
        row = self.row.copy()
        row[index] = value
        return row

    def write_csv(self, rows, header=True):
        """rowsをLF改行のUTF-8でCSVに書き出す。headerがFalseならヘッダーを省く。"""
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        if header:
            writer.writerow(COLUMNS)
        writer.writerows(rows)
        self.path.write_bytes(stream.getvalue().encode("utf-8"))

    def test_valid_csv_and_quoted_fields(self):
        self.row[3] = '出典, "引用"'
        self.write_csv([self.row, ["よみ", "表記", "proper_noun", ""]])
        self.assertEqual(
            load_entries(self.path),
            [Entry(*self.row), Entry("よみ", "表記", "proper_noun", "")],
        )

    def test_required_values(self):
        for index in (0, 1):
            for value in ("", "  "):
                with self.subTest(index=index, value=value):
                    self.write_csv([self.replaced_row(index, value)])
                    with self.assertRaisesRegex(ValueError, "必須"):
                        load_entries(self.path)

    def test_invalid_pos(self):
        for value in ("", "noun", "固有名詞"):
            with self.subTest(value=value):
                self.write_csv([self.replaced_row(2, value)])
                with self.assertRaisesRegex(ValueError, "不正なpos"):
                    load_entries(self.path)

    def test_forbidden_characters_in_every_field(self):
        for index in range(4):
            for char in "\t\r\n\0":
                with self.subTest(index=index, char=repr(char)):
                    self.write_csv([self.replaced_row(index, self.row[index] + char)])
                    with self.assertRaisesRegex(ValueError, "禁止|使えません"):
                        load_entries(self.path)

    def test_non_nfc_in_every_field_is_rejected_without_rewriting(self):
        for index in range(4):
            with self.subTest(index=index):
                decomposed = "か\u3099"  # 結合用濁点付き。NFCでは「が」1文字になる
                self.write_csv([self.replaced_row(index, self.row[index] + decomposed)])
                original = self.path.read_bytes()
                with self.assertRaisesRegex(ValueError, "NFC"):
                    load_entries(self.path)
                self.assertEqual(self.path.read_bytes(), original)

    def test_duplicate_ignores_note(self):
        self.write_csv([self.row, self.row[:3] + ["別の注記"]])
        with self.assertRaisesRegex(ValueError, "重複"):
            load_entries(self.path)

    def test_same_reading_with_different_term_is_allowed(self):
        self.write_csv([self.row, [self.row[0], "別表記", "proper_noun", ""]])
        self.assertEqual(len(load_entries(self.path)), 2)

    def test_header_column_count_and_csv_syntax(self):
        for text in (
            "",  # 空ファイル
            ",".join(self.row) + "\n",  # ヘッダーなし
            "term,reading,pos,note\n",  # 列順違い
            "reading,term,pos,note\nよみ,表記,proper_noun\n",  # 列不足
            "reading,term,pos,note\nよみ,表記,proper_noun,,余分\n",  # 列過多
            'reading,term,pos,note\n"閉じない引用',  # 引用符が閉じない
            'reading,term,pos,note\n"よみ"x,表記,proper_noun,\n',  # 引用符の後に文字
        ):
            with self.subTest(text=text):
                self.path.write_bytes(text.encode("utf-8"))
                with self.assertRaises(ValueError):
                    load_entries(self.path)

    def test_encoding_bom_and_record_newlines(self):
        self.write_csv([self.row])
        valid = self.path.read_bytes()
        for data in (codecs.BOM_UTF8 + valid, valid.replace(b"\n", b"\r\n"), b"\xff"):
            with self.subTest(data=data):
                self.path.write_bytes(data)
                with self.assertRaises(ValueError):
                    load_entries(self.path)

    def test_microsoft_bytes_and_pos_mapping(self):
        expected = "!Microsoft IME Dictionary Tool\r\nきさらぎこうむてん\t如月工務店\t固有名詞\t\r\nよみ\t表記\t固有名詞\t注記,引用\r\n"
        data = export_microsoft(self.entries)
        self.assertEqual(data[:2], b"\xff\xfe")
        self.assertEqual(data, b"\xff\xfe" + expected.encode("utf-16-le"))
        self.assertEqual(data.decode("utf-16"), expected)

    def test_google_utf8_tabs_and_pos_mapping(self):
        expected = "きさらぎこうむてん\t如月工務店\t固有名詞\t\nよみ\t表記\t固有名詞\t注記,引用\n"
        data = export_google(self.entries)
        self.assertEqual(data, expected.encode("utf-8"))
        self.assertFalse(data.startswith(codecs.BOM_UTF8))

    def test_build_files_and_preserve_outputs_on_validation_error(self):
        self.write_csv([self.row])
        output = Path(self.temp.name) / "dist"
        self.assertEqual(build(self.path, output), 1)
        files = {path.name: path.read_bytes() for path in output.iterdir()}
        self.assertEqual(
            files,
            {
                MICROSOFT_FILE: export_microsoft([Entry(*self.row)]),
                GOOGLE_FILE: export_google([Entry(*self.row)]),
            },
        )
        # 重複エラーになるCSVで再生成しても、
        # 先に生成したファイルが上書きされず残ることを確認する。
        self.write_csv([self.row, self.row])
        with self.assertRaises(ValueError):
            build(self.path, output)
        self.assertEqual(
            {path.name: path.read_bytes() for path in output.iterdir()}, files
        )

    def test_repository_source_and_cli_from_other_directory(self):
        entries = load_entries(ROOT / "data/dictionary.csv")
        self.assertGreater(len(entries), 0)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build.py")],
            cwd=self.temp.name,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (ROOT / "dist" / MICROSOFT_FILE).read_bytes(), export_microsoft(entries)
        )
        self.assertEqual(
            (ROOT / "dist" / GOOGLE_FILE).read_bytes(),
            export_google(entries),
        )


if __name__ == "__main__":
    unittest.main()
