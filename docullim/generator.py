import glob
import hashlib
import importlib.util
import inspect
import os
import sys
import ast
import libcst as cst
from libcst import matchers as m
from litellm import completion


def generate_doc(source_code: str, model: str, prompt_template: str) -> str:
    """
    Generate documentation for the provided source code using the specified model and prompt template.
    """
    prompt = f"{prompt_template}\n{source_code}"
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        doc = response.choices[0].message.content.strip()
    except Exception as e:
        doc = f"Error generating documentation: {e}"
    return doc


def hash_source(source: str) -> str:
    """
    Compute a SHA256 hash of the given source string.
    """
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def remove_existing_docstring(source: str) -> str:
    """
    Remove the existing docstring from the provided source code.

    This function parses the source as an AST and, for each top-level function, async function,
    or class node, removes the first statement if it is a docstring. The resulting AST is then
    unparsed back into source code.

    If any error occurs during parsing or unparsing, the original source is returned.
    """
    try:
        tree = ast.parse(source)
        # Process each top-level node in the module.
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    # Remove the docstring (the first statement)
                    node.body = node.body[1:]
        return ast.unparse(tree)
    except Exception as e:
        # If parsing fails, return the original source.
        return source


def process_file(file_path: str, config: dict, cache=None, write: bool = False) -> dict:
    """
    Process a single Python file. For every function or class decorated with @docullim,
    generate documentation using the appropriate prompt template (based on the tag) and model.
    Utilizes a cache (if provided) to avoid redundant API calls.

    If write is True, update the source file by replacing or inserting the generated docstring
    for each decorated object.
    """
    docs = {}
    modifications = {}  # Mapping from function/class name to new docstring.
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            print(f"Could not load module from {file_path}", file=sys.stderr)
            return docs
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error importing {file_path}: {e}", file=sys.stderr)
        return docs

    model = config.get("model", "gpt-4")
    prompts = config.get("prompts", {})
    default_prompt = prompts.get("default")

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (callable(attr) or isinstance(attr, type)) and getattr(
            attr, "_auto_doc", False
        ):
            try:
                source = inspect.getsource(attr)
            except Exception as e:
                source = f"# Could not retrieve source: {e}"
            # Remove any existing docstring from the source code before sending to LLM.
            source = remove_existing_docstring(source)
            tag = getattr(attr, "_auto_doc_tag", None)
            prompt_template = (
                prompts.get(tag, default_prompt) if tag else default_prompt
            )

            # Create a cache key based on the source code (without the existing docstring) and the prompt template.
            key = hash_source(source + prompt_template)
            doc = None
            if cache is not None:
                doc = cache.get(key)
            if doc is None:
                doc = generate_doc(source, model, prompt_template)
                if cache is not None:
                    cache.set(key, doc)
            docs[attr_name] = doc

            if write:
                modifications[attr_name] = doc

    if write and modifications:
        update_docstrings_in_file(file_path, modifications)

    return docs


def update_docstrings_in_file(file_path: str, modifications: dict[str, str]) -> None:
    """
    Update or insert docstrings in the given file using LibCST,
    preserving the original formatting as much as possible.

    modifications: A mapping from function or class names to the new docstring.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        module = cst.parse_module(source)
        updater = DocStringUpdater(modifications)
        modified_module = module.visit(updater)
        new_source = modified_module.code
    except Exception as e:
        print(f"Error updating docstrings in {file_path}: {e}", file=sys.stderr)
        return
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_source)


def collect_files(patterns):
    """
    Given a list of file paths or glob patterns, return a deduplicated list of matching files.
    """
    files_set = set()
    for pattern in patterns:
        if any(wildcard in pattern for wildcard in ["*", "?", "[", "]"]):
            expanded = glob.glob(pattern, recursive=True)
            files_set.update(expanded)
        else:
            if os.path.exists(pattern):
                files_set.add(pattern)
            else:
                print(
                    f"Warning: File or pattern '{pattern}' does not exist.",
                    file=sys.stderr,
                )
    return list(files_set)


def _make_docstring_node(doc: str) -> cst.SimpleStatementLine:
    """
    Create a SimpleStatementLine representing a docstring.
    Uses triple quotes for the docstring.
    """
    # We force triple double quotes. You can adjust this if needed.
    docstring = f'"""{doc}"""'
    return cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString(docstring))])


class DocStringUpdater(cst.CSTTransformer):
    def __init__(self, modifications: dict[str, str]):
        """
        modifications: Mapping from function or class name to the new docstring.
        """
        super().__init__()
        self.modifications = modifications

    def _update_docstring(self, node, new_doc: str) -> list[cst.CSTNode]:
        """
        Given a node (which might be a docstring node) and a new docstring,
        return a new list of nodes that represents the updated docstring.
        """
        return [_make_docstring_node(new_doc)]

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        func_name = original_node.name.value
        if func_name in self.modifications:
            new_doc = self.modifications[func_name]
            body = updated_node.body.body
            if body and m.matches(
                body[0], m.SimpleStatementLine(body=[m.Expr(m.SimpleString())])
            ):
                # Replace existing docstring node.
                new_body = self._update_docstring(body[0], new_doc) + list(body[1:])
            else:
                # Insert new docstring node at the beginning.
                new_body = self._update_docstring(None, new_doc) + list(body)
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        class_name = original_node.name.value
        if class_name in self.modifications:
            new_doc = self.modifications[class_name]
            body = updated_node.body.body
            if body and m.matches(
                body[0], m.SimpleStatementLine(body=[m.Expr(m.SimpleString())])
            ):
                new_body = self._update_docstring(body[0], new_doc) + list(body[1:])
            else:
                new_body = self._update_docstring(None, new_doc) + list(body)
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        return updated_node
