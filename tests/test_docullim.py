import json
import textwrap

from docullim import docullim
from docullim.cli import process_file, main


def test_docullim_decorator():
    @docullim
    def dummy_function():
        return "dummy"

    # Check that the dummy_function has the _auto_doc attribute.
    assert getattr(dummy_function, "_auto_doc", False) is True


def test_process_file(tmp_path):
    # Create a temporary Python file that uses the docullim decorator.
    file_content = textwrap.dedent("""
        from docullim import docullim

        @docullim
        def add(a, b):
            return a + b
    """)
    temp_file = tmp_path / "temp_module.py"
    temp_file.write_text(file_content)

    # Process the temporary file.
    docs = process_file(str(temp_file), config={}, cache=None)
    # We expect 'add' to be documented.
    assert "add" in docs
    # Check that the documentation is a non-empty string.
    assert isinstance(docs["add"], str)
    assert len(docs["add"]) > 0


def test_cli(monkeypatch, tmp_path, capsys):
    # Create a temporary Python file for testing the CLI.
    file_content = textwrap.dedent("""
        from docullim import docullim

        @docullim
        def subtract(a, b):
            return a - b
    """)
    temp_file = tmp_path / "temp_cli_module.py"
    temp_file.write_text(file_content)

    # Simulate command-line arguments.
    monkeypatch.setattr("sys.argv", ["docullim", str(temp_file)])
    # Run the CLI main function.
    main()
    # Capture the output.
    captured = capsys.readouterr().out
    # Parse the output JSON.
    output_json = json.loads(captured)
    # Ensure the temporary file is in the JSON output and that 'subtract' is documented.
    assert str(temp_file) in output_json
    assert "subtract" in output_json[str(temp_file)]
