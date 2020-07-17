import unittest
import os
import pathlib
import shutil
import sys
import tempfile

import check50
import check50.internal

from bases import PythonBase

class TestInclude(PythonBase):
    def setUp(self):
        super().setUp()
        self._old_check_dir = check50.internal.check_dir
        os.mkdir("bar")
        with open("./bar/baz.txt", "w") as f:
            pass
        check50.internal.check_dir = pathlib.Path("./bar").absolute()

    def tearDown(self):
        super().tearDown()
        check50.internal.check_dir = self._old_check_dir

    def test_include(self):
        check50.include("baz.txt")
        self.assertTrue((pathlib.Path(".").absolute() / "baz.txt").exists())
        self.assertTrue((check50.internal.check_dir / "baz.txt").exists())

class TestExists(PythonBase):
    def test_file_does_not_exist(self):
        with self.assertRaises(check50.Failure):
            check50.exists("i_do_not_exist")

    def test_file_exists(self):
        check50.exists(self.filename)


class TestImportChecks(PythonBase):
    def setUp(self):
        super().setUp()
        self._old_check_dir = check50.internal.check_dir
        os.mkdir("bar")
        check50.internal.check_dir = pathlib.Path(".").absolute()

    def tearDown(self):
        super().tearDown()
        check50.internal.check_dir = self._old_check_dir

    def test_simple_import(self):
        with open(".cs50.yaml", "w") as f:
            f.write("check50:\n")
            f.write("  checks: foo.py")
        mod = check50.import_checks(".")
        self.assertEqual(mod.__name__, pathlib.Path(self.working_directory.name).name)

    def test_relative_import(self):
        with open("./bar/baz.py", "w") as f:
            f.write("qux = 0")

        with open("./bar/.cs50.yaml", "w") as f:
            f.write("check50:\n")
            f.write("  checks: baz.py")

        mod = check50.import_checks("./bar")
        self.assertEqual(mod.__name__, "bar")
        self.assertEqual(mod.qux, 0)


class TestRun(PythonBase):
    def test_returns_process(self):
        self.process = check50.run("python3 ./{self.filename}")


class TestProcessKill(PythonBase):
    def test_kill(self):
        self.runpy()
        self.assertTrue(self.process.process.isalive())
        self.process.kill()
        self.assertFalse(self.process.process.isalive())

class TestProcessStdin(PythonBase):
    def test_expect_prompt_no_prompt(self):
        self.write("x = input()")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdin("bar")

    def test_expect_prompt(self):
        self.write("x = input('foo')")
        self.runpy()
        self.process.stdin("bar")
        self.assertTrue(self.process.process.isalive())

    def test_no_prompt(self):
        self.write("x = input()\n")
        self.runpy()
        self.process.stdin("bar", prompt=False)
        self.assertTrue(self.process.process.isalive())

class TestProcessStdout(PythonBase):
    def test_no_out(self):
        self.runpy()
        out = self.process.stdout(timeout=1)
        self.assertEqual(out, "")
        self.assertFalse(self.process.process.isalive())

        self.write("print('foo')")
        self.runpy()
        out = self.process.stdout()
        self.assertEqual(out, "foo\n")
        self.assertFalse(self.process.process.isalive())

    def test_out(self):
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout("foo")
        self.assertFalse(self.process.process.isalive())

        self.write("print('foo')")
        self.runpy()
        self.process.stdout("foo\n")

    def test_outs(self):
        self.write("print('foo')\nprint('bar')\n")
        self.runpy()
        self.process.stdout("foo\n")
        self.process.stdout("bar")
        self.process.stdout("\n")

    def test_out_regex(self):
        self.write("print('foo')")
        self.runpy()
        self.process.stdout(".o.")
        self.process.stdout("\n")

    def test_out_no_regex(self):
        self.write("print('foo')")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(".o.", regex=False)
        self.assertFalse(self.process.process.isalive())

    def test_int(self):
        self.write("print(123)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(1)

        self.write("print(21)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(1)

        self.write("print(1.0)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(1)

        self.write("print('a1b')")
        self.runpy()
        self.process.stdout(1)

        self.write("print(1)")
        self.runpy()
        self.process.stdout(1)

    def test_float(self):
        self.write("print(1.01)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(1.0)

        self.write("print(21.0)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(1.0)

        self.write("print(1)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(1.0)

        self.write("print('a1.0b')")
        self.runpy()
        self.process.stdout(1.0)

        self.write("print(1.0)")
        self.runpy()
        self.process.stdout(1.0)

    def test_negative_number(self):
        self.write("print(1)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(-1)

        self.write("print(-1)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.stdout(1)

        self.write("print('2-1')")
        self.runpy()
        self.process.stdout(-1)

        self.write("print(-1)")
        self.runpy()
        self.process.stdout(-1)


class TestProcessStdoutFile(PythonBase):
    def setUp(self):
        super().setUp()
        self.txt_filename = "foo.txt"
        with open(self.txt_filename, "w") as f:
            f.write("foo")

    def test_file(self):
        self.write("print('bar')")
        self.runpy()
        with open(self.txt_filename, "r") as f:
            with self.assertRaises(check50.Failure):
                self.process.stdout(f, regex=False)

        self.write("print('foo')")
        self.runpy()
        with open(self.txt_filename, "r") as f:
            self.process.stdout(f, regex=False)

    def test_file_regex(self):
        self.write("print('bar')")
        with open(self.txt_filename, "w") as f:
            f.write(".a.")
        self.runpy()
        with open(self.txt_filename, "r") as f:
            self.process.stdout(f)

class TestProcessExit(PythonBase):
    def test_exit(self):
        self.write("sys.exit(1)")
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.exit(0)
        self.process.kill()

        self.write("sys.exit(1)")
        self.runpy()
        self.process.exit(1)

    def test_no_exit(self):
        self.write("sys.exit(1)")
        self.runpy()
        exit_code = self.process.exit()
        self.assertEqual(exit_code, 1)

class TestProcessKill(PythonBase):
    def test_kill(self):
        self.runpy()
        self.process.kill()
        self.assertFalse(self.process.process.isalive())

class TestProcessReject(PythonBase):
    def test_reject(self):
        self.write("input()")
        self.runpy()
        self.process.reject()
        self.process.stdin("foo", prompt=False)
        with self.assertRaises(check50.Failure):
            self.process.reject()

    def test_no_reject(self):
        self.runpy()
        with self.assertRaises(check50.Failure):
            self.process.reject()

if __name__ == '__main__':
    unittest.main()
