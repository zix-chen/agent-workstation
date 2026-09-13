import unittest
from agent_workstation.output_policy import command_preview, excerpt


class OutputTests(unittest.TestCase):
    def segments(self, stdout, stderr=b""):
        return lambda name: (
            b"",
            stdout if name == "stdout" else stderr,
            0,
            len(stdout if name == "stdout" else stderr),
            0,
        )

    def test_small_output_intact(self):
        value, omitted = command_preview(self.segments(b"hello"), 8192)
        self.assertIn("hello", value)
        self.assertEqual(omitted, [])

    def test_empty_output(self):
        self.assertEqual(command_preview(self.segments(b""), 8192), ("", []))

    def test_stdout_and_stderr_head_tail(self):
        out = b"OUT_BEGIN" + b"x" * 40000 + b"OUT_END"
        err = b"ERR_BEGIN" + b"y" * 30000 + b"ERR_END"
        text, omitted = command_preview(self.segments(out, err), 8192)
        for marker in ("OUT_BEGIN", "OUT_END", "ERR_BEGIN", "ERR_END"):
            self.assertIn(marker, text)
        self.assertEqual(omitted, ["stdout", "stderr"])
        self.assertLessEqual(len(text.encode()), 8192)

    def test_short_error_stream_not_starved(self):
        value, _ = command_preview(self.segments(b"x" * 100000, b"IMPORTANT_ERROR"), 1024)
        self.assertIn("IMPORTANT_ERROR", value)

    def test_utf8_and_tiny_budgets(self):
        segments = self.segments(("开头" + "中" * 9000 + "结尾").encode(), b"ERROR")
        for limit in (0, 1, 20, 512, 8192):
            text, _ = command_preview(segments, limit)
            self.assertLessEqual(len(text.encode()), limit)
            self.assertNotIn("\ufffd", text)

    def test_retention_gap_reported(self):
        def segments(name):
            return (b"BEGIN", b"END", 100, 103, 95) if name == "stdout" else (b"", b"", 0, 0, 0)

        value, omitted = command_preview(segments, 8192)
        self.assertIn("retained output gap", value)
        self.assertEqual(omitted, ["stdout"])

    def test_excerpt_prefers_tail(self):
        self.assertEqual(excerpt(b"0123456789", 3), b"789")
