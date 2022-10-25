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
    @abc.abstractmethod
    def __init__(self):
        self.should_recurse_children = True

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
    def __init__(self):
        super().__init__()
        self.data = None

    def __iadd__(self, other):
        super().__iadd__(other)
        if not (isinstance(other, NoResult) or other is None):
            warnings.warn(f"result {other} is not None")
        return self


class IntegerResult(NodeTraversalResult):
    def __init__(self, data=0):
        super().__init__()
        self.data = data

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


def dfs(node, fn, result_cls=NoResult, indent=0, **kwargs):
    result = result_cls()
    result += fn(node=node, indent=indent, **kwargs) or 0
    if not result.should_recurse_children:
        return result
    for c in node.children:
        result += dfs(c, fn, result_cls=result_cls, indent=indent + 1, **kwargs) or 0
    return result


def get_children(node, fn):
    return [c for c in node.children if fn(c)]


def get_child(node, fn):
    return next(iter(get_children(node, fn)))


#%%
# print all nodes, stop at class declaration


def print_node_stop_at_import(node, indent, **kwargs):
    text = node.text.decode()
    if "\n" in text:
        text = text.splitlines(keepends=False)[0] + "..."
    print(" " * (indent * 2), node, text)

    result = NoResult()
    if node.type == "import_declaration":
        result.should_recurse_children = False
    return result


def parse_print(filename):
    tree = parse_file(filename)
    print(tree)
    dfs(tree.root_node, fn=print_node_stop_at_import)


parse_print(
    "/home/benjis/code/bug-benchmarks/defects4j/projects/Chart_1b/tests/org/jfree/chart/annotations/junit/CategoryLineAnnotationTests.java"
)


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


def declare_class(node, class_name, **kwargs):
    count = 0
    if node.type == "class_declaration":
        ident = get_child(node, lambda c: c.type == "identifier")
        if ident.text.decode() == class_name:
            body = get_child(node, lambda c: c.type == "class_body")
            test_methods = get_children(body, lambda c: c.type == "method_declaration")
            for test_method in test_methods:
                method_ident = get_child(
                    test_method, lambda c: c.type == "identifier"
                ).text.decode()
                if method_ident.startswith("test"):
                    count += 1
    return count


def parse_test_class(filename, class_name):
    tree = parse_file(filename)
    return dfs(
        tree.root_node,
        fn=declare_class,
        result_cls=IntegerResult,
        class_name=class_name,
    )


parse_test_class(
    "/home/benjis/code/bug-benchmarks/defects4j/projects/Chart_1b/tests/org/jfree/chart/annotations/junit/CategoryLineAnnotationTests.java",
    "CategoryLineAnnotationTests",
)

#%%
# print number of test methods in each class/project/total
import re

projects_root = "/home/benjis/code/bug-benchmarks/defects4j/projects"
all_num_methods = 0
for project in projects:
    project_num_methods = 0
    project_root = os.path.join(projects_root, project + "_1b")
    with open(os.path.join(project_root, "defects4j.build.properties")) as properties_f:
        test_prefix = re.findall(r"d4j.dir.src.tests=(.*)", properties_f.read())[0]
    with open(os.path.join(project_root, "tests.all")) as test_f:
        for test_class in test_f:
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
            num_methods = parse_test_class(test_filepath, class_name)
            print(test_class, "class had", num_methods, "test methods")
            project_num_methods += num_methods
    print(project, "project had", project_num_methods, "test methods")
    all_num_methods += project_num_methods
print(all_num_methods, "total test methods")

# %%
