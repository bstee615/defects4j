#%%
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

#%%
# projects = ["Chart"]
with open("/home/benjis/code/bug-benchmarks/defects4j/projects.txt") as f:
    projects = f.read().splitlines(keepends=False)
projects

#%%
import re

projects_root = "/home/benjis/code/bug-benchmarks/defects4j/projects"
for project in projects:
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

#%%


def dfs(node, fn, indent=0, **kwargs):
    fn(node=node, indent=indent, **kwargs)
    for c in node.children:
        dfs(c, fn, indent + 1, **kwargs)


def bfs(root, fn, **kwargs):
    q = [(root, 0)]
    while len(q) > 0:
        n, indent = q.pop(0)

        fn(node=n, indent=indent, **kwargs)

        for c in n.children:
            q.append((c, indent + 1))


def print_node(node, indent, **kwargs):
    text = node.text.decode()
    if "\n" in text:
        text = text.splitlines(keepends=False)[0] + "..."
    print(" " * (indent * 2), node, text)


def declare_class(node, class_name, **kwargs):
    if node.type == "class_declaration":
        ident = next(
            (
                c
                for c in node.children
                if c.type == "identifier" and c.text.decode() == class_name
            ),
            None,
        )
        if ident is not None:
            print("got class", node)
        else:
            print(node, "could not get class")


def parse_test_class(filename, class_name):
    with open(filename, "rb") as f:
        tree = parser.parse(f.read())
    print(tree)
    dfs(tree.root_node, print_node, class_name=class_name)
    dfs(tree.root_node, declare_class, class_name=class_name)


parse_test_class(
    "/home/benjis/code/bug-benchmarks/defects4j/projects/Chart_1b/tests/org/jfree/chart/annotations/junit/CategoryLineAnnotationTests.java",
    "CategoryLineAnnotationTests",
)

# %%
