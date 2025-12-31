"""
Contains functions to manually generate a textual preview of some common file types (.csv, .json,..) for the agent.
"""

import json
from pathlib import Path

import humanize
import pandas as pd
from genson import SchemaBuilder
from pandas.api.types import is_numeric_dtype

# these files are treated as code (e.g. markdown wrapped)
code_files = {".py", ".sh", ".yaml", ".yml", ".md", ".html", ".xml", ".log", ".rst"}
# we treat these files as text (rather than binary) files
plaintext_files = {".txt", ".csv", ".json", ".tsv"} | code_files


def get_file_len_size(f: Path) -> tuple[int, str]:
    """
    Calculate the size of a file (#lines for plaintext files, otherwise #bytes)
    Also returns a human-readable string representation of the size.
    """
    if f.suffix in plaintext_files:
        # Try UTF-8 first, then common Kaggle encodings (cp1252 / latin-1)
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                with open(f, encoding=enc, errors="strict") as fh:
                    num_lines = sum(1 for _ in fh)
                return num_lines, f"{num_lines} lines"
            except UnicodeDecodeError:
                continue

    # Fallback: treat as binary, report size in bytes
    s = f.stat().st_size
    return s, humanize.naturalsize(s)


def file_tree(path: Path, depth=0) -> str:
    """Generate a tree structure of files in a directory"""
    result = []
    files = [p for p in Path(path).iterdir() if not p.is_dir()]
    dirs = [p for p in Path(path).iterdir() if p.is_dir()]
    max_n = 4 if len(files) > 30 else 8
    for p in sorted(files)[:max_n]:
        result.append(f"{' ' * depth * 4}{p.name} ({get_file_len_size(p)[1]})")
    if len(files) > max_n:
        result.append(f"{' ' * depth * 4}... and {len(files) - max_n} other files")

    for p in sorted(dirs):
        result.append(f"{' ' * depth * 4}{p.name}/")
        result.append(file_tree(p, depth + 1))

    return "\n".join(result)


def _walk(path: Path):
    """Recursively walk a directory (analogous to os.walk but for pathlib.Path)"""
    for p in sorted(Path(path).iterdir()):
        if p.is_dir():
            yield from _walk(p)
            continue
        yield p


def preview_csv(p: Path, file_name: str, simple=True) -> str:
    """Generate a textual preview of a csv file

    Args:
        p (Path): the path to the csv file
        file_name (str): the file name to use in the preview
        simple (bool, optional): whether to use a simplified version of the preview. Defaults to True.

    Returns:
        str: the textual preview
    """
    # Home Credit 等 Kaggle 数据集中，部分 CSV（如 installments_payments.csv）
    # 使用 cp1252/latin-1 编码，这里做编码回退处理。
    last_error: Exception | None = None
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(p, encoding=enc)
            break
        except UnicodeDecodeError as e:
            last_error = e
            continue
    else:
        # 所有尝试都失败时，返回友好提示，避免程序崩溃
        return (
            f"-> {file_name} could not be decoded as UTF-8/cp1252/latin-1. "
            f"Last error: {last_error}"
        )

    out = []

    out.append(f"-> {file_name} has {df.shape[0]} rows and {df.shape[1]} columns.")

    if simple:
        cols = df.columns.tolist()
        sel_cols = 15
        cols_str = ", ".join(cols[:sel_cols])
        res = f"The columns are: {cols_str}"
        if len(cols) > sel_cols:
            res += f"... and {len(cols) - sel_cols} more columns"
        out.append(res)
    else:
        out.append("Here is some information about the columns:")
        for col in sorted(df.columns):
            dtype = df[col].dtype
            name = f"{col} ({dtype})"

            nan_count = df[col].isnull().sum()

            if dtype == "bool":
                v = df[col][df[col].notnull()].mean()
                out.append(f"{name} is {v * 100:.2f}% True, {100 - v * 100:.2f}% False")
            elif df[col].nunique() < 10:
                out.append(
                    f"{name} has {df[col].nunique()} unique values: {df[col].unique().tolist()}"
                )
            elif is_numeric_dtype(df[col]):
                out.append(
                    f"{name} has range: {df[col].min():.2f} - {df[col].max():.2f}, {nan_count} nan values"
                )
            elif dtype == "object":
                out.append(
                    f"{name} has {df[col].nunique()} unique values. Some example values: {df[col].value_counts().head(4).index.tolist()}"
                )

    return "\n".join(out)


def preview_json(p: Path, file_name: str):
    """Generate a textual preview of a json file using a generated json schema"""
    builder = SchemaBuilder()
    # JSON 一般是 UTF-8，但也做一次 cp1252/latin-1 兜底
    last_error: Exception | None = None
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            with open(p, encoding=enc) as f:
                builder.add_object(json.load(f))
            break
        except UnicodeDecodeError as e:
            last_error = e
            continue
    else:
        return (
            f"-> {file_name} could not be decoded as UTF-8/cp1252/latin-1. "
            f"Last error: {last_error}"
        )
    return f"-> {file_name} has auto-generated json schema:\n" + builder.to_json(
        indent=2
    )


def generate(base_path, include_file_details=True, simple=False):
    """
    Generate a textual preview of a directory, including an overview of the directory
    structure and previews of individual files
    """
    tree = f"```\n{file_tree(base_path)}```"
    out = [tree]

    if include_file_details:
        for fn in _walk(base_path):
            file_name = str(fn.relative_to(base_path))

            if fn.suffix == ".csv":
                out.append(preview_csv(fn, file_name, simple=simple))
            elif fn.suffix == ".json":
                out.append(preview_json(fn, file_name))
            elif fn.suffix in plaintext_files:
                if get_file_len_size(fn)[0] < 30:
                    # For small text files, try multiple encodings similar to CSV handling.
                    content = None
                    last_error: Exception | None = None
                    for enc in ("utf-8", "cp1252", "latin-1"):
                        try:
                            with open(fn, encoding=enc) as f:
                                content = f.read()
                            break
                        except UnicodeDecodeError as e:
                            last_error = e
                            continue

                    if content is None:
                        out.append(
                            f"-> {file_name} content could not be decoded as "
                            f"UTF-8/cp1252/latin-1. Last error: {last_error}"
                        )
                    else:
                        if fn.suffix in code_files:
                            content = f"```\n{content}\n```"
                        out.append(f"-> {file_name} has content:\n\n{content}")

    result = "\n\n".join(out)

    # if the result is very long we generate a simpler version
    if len(result) > 6_000 and not simple:
        return generate(
            base_path, include_file_details=include_file_details, simple=True
        )

    return result
