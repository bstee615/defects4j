#%%
from typing import overload
from tree_sitter import Language, Parser
import os


TREE_SITTER_LIB_PREFIX = "/home/benjis/code/bug-benchmarks/defects4j/parse"


languages = ["java"]
language_dirs = []

for lang in languages:
    clone_dir = os.path.join(TREE_SITTER_LIB_PREFIX, f"tree-sitter-{lang}")
    language_dirs.append(clone_dir)

lib_file = os.path.join(TREE_SITTER_LIB_PREFIX, "build/languages.so")
Language.build_library(
    # Store the library in the `build` directory
    lib_file,
    # Include one or more languages
    [
        os.path.join(TREE_SITTER_LIB_PREFIX, f"tree-sitter-{lang}"),
    ],
)

LANGUAGE = Language(lib_file, languages[0])
parser = Parser()
parser.set_language(LANGUAGE)


def parse_file(filename):
    with open(filename, "rb") as f:
        tree = parser.parse(f.read())
    return tree


#%%
# get all projects in d4j
with open("/home/benjis/code/bug-benchmarks/defects4j/projects.txt") as f:
    projects = f.read().splitlines(keepends=False)
projects

#%%
# utilities for general tree traversal
import abc
import warnings
import copy


class NodeTraversalResult(abc.ABC):
    def __init__(self, data=None):
        if data is None:
            self.data = self.default()
        else:
            self.data = None
        self.should_recurse_children = True

    @abc.abstractclassmethod
    def default(cls):
        pass

    def __iadd__(self, other):
        if isinstance(other, NodeTraversalResult):
            self.should_recurse_children &= other.should_recurse_children
        return self

    def __str__(self) -> str:
        return str(self.data)

    def __repr__(self):
        return str(self)

    def stop(self):
        self.should_recurse_children = False


class NoResult(NodeTraversalResult):
    @classmethod
    def default(cls):
        return None

    def __iadd__(self, other):
        super().__iadd__(other)
        if not (isinstance(other, NoResult) or other is None):
            warnings.warn(f"result {other} is not None")
        return self


class IntegerResult(NodeTraversalResult):
    @classmethod
    def default(cls):
        return 0

    def __iadd__(self, other):
        super().__iadd__(other)
        if isinstance(other, IntegerResult):
            other_data = other.data
        else:
            other_data = other
        self.data += other_data
        return self

    def __add__(self, other):
        result = copy.deepcopy(self)
        result += other
        return result

    def __radd__(self, other):
        return self.data + other


class ListResult(NodeTraversalResult):
    @classmethod
    def default(cls):
        return []

    def __iadd__(self, other):
        super().__iadd__(other)
        if isinstance(other, ListResult):
            other_data = other.data
        else:
            other_data = other
        self.data += other_data
        return self

    def __add__(self, other):
        result = copy.deepcopy(self)
        result += other
        return result

    def __radd__(self, other):
        return self.data + other


def dfs(node, fn, result_cls=NoResult, indent=0, **kwargs):
    result = result_cls()
    fn_result = (
        fn(node=node, indent=indent, result_cls=result_cls, **kwargs)
        or result_cls.default()
    )
    result += fn_result
    if not result.should_recurse_children:
        return result
    for c in node.children:
        result += (
            dfs(c, fn, result_cls=result_cls, indent=indent + 1, **kwargs)
            or result_cls.default()
        )
    return result


def get_children(node, fn):
    return [c for c in node.children if fn(c)]


def get_child(node, fn):
    return next(iter(get_children(node, fn)))


#%%


def print_node(node, indent, **kwargs):
    text = node.text.decode()
    if "\n" in text:
        text = text.splitlines(keepends=False)[0] + "..."
    print(" " * (indent * 2), node, text)


def parse_print(filename):
    tree = parse_file(filename)
    print(tree)
    dfs(tree.root_node, fn=print_node)


parse_print(
    "/home/benjis/code/bug-benchmarks/defects4j/projects/Chart_1b/tests/org/jfree/chart/annotations/junit/CategoryLineAnnotationTests.java"
)


#%%


def print_method_length(node, **kwargs):
    if node.type == "method_declaration":
        method_text = node.text.decode()
        return [{"tokens": len(method_text), "lines": len(method_text.splitlines())}]
    return []


def test_method_length(filename):
    tree = parse_file(filename)
    return dfs(
        tree.root_node,
        fn=print_method_length,
        result_cls=ListResult,
    )


test_method_length(
    "/home/benjis/code/bug-benchmarks/defects4j/projects/Chart_1b/tests/org/jfree/chart/annotations/junit/CategoryLineAnnotationTests.java"
)

#%%
# print number of filenames in all test methods
import re
import numpy as np
import tqdm as tqdm

projects_root = "/home/benjis/code/bug-benchmarks/defects4j/projects"
all_data = {
    "tokens": [],
    "lines": [],
}
for project in tqdm.tqdm(projects, desc="projects"):
    project_root = os.path.join(projects_root, project + "_1b")
    with open(os.path.join(project_root, "defects4j.build.properties")) as properties_f:
        test_prefix = re.findall(r"d4j.dir.src.tests=(.*)", properties_f.read())[0]
    with open(os.path.join(project_root, "tests.all")) as test_f:
        test_classes = test_f.readlines()
        # test_classes = tqdm.tqdm(test_classes, position=1, desc="classes")
        for test_class in test_classes:
            test_class = test_class.strip()
            test_filename = "/".join(test_class.split("."))
            if "$" in test_filename:
                test_filename, class_name = test_filename.split("$")
            else:
                class_name = test_class.split(".")[-1]
            test_filepath = os.path.join(
                projects_root, project + "_1b", test_prefix, test_filename + ".java"
            )
            if not os.path.exists(test_filepath):
                print(
                    "could not locate class for test", project, test_prefix, test_class
                )
                continue

            method_lengths = test_method_length(test_filepath)
            for d in method_lengths.data:
                all_data["tokens"].append(d["tokens"])
                all_data["lines"].append(d["lines"])

print("average method had", np.average(all_data["tokens"]), "tokens")
print("average method had", np.average(all_data["lines"]), "lines")

# %%
