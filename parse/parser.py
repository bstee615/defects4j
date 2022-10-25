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


def parse_file(filename):
    with open(filename, "rb") as f:
        tree = parser.parse(f.read())
    return tree


#%%
# projects = ["Chart"]
with open("/home/benjis/code/bug-benchmarks/defects4j/projects.txt") as f:
    projects = f.read().splitlines(keepends=False)
projects

#%%


def dfs(node, fn, indent=0, **kwargs):
    result = 0
    result += fn(node=node, indent=indent, **kwargs)
    for c in node.children:
        result += dfs(c, fn, indent + 1, **kwargs)
    return result


def bfs(root, fn, **kwargs):
    result = 0
    q = [(root, 0)]
    while len(q) > 0:
        n, indent = q.pop(0)

        result += fn(node=n, indent=indent, **kwargs)

        for c in n.children:
            result += q.append((c, indent + 1))
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


def parse_print(filename, class_name):
    tree = parse_file(filename)
    print(tree)
    dfs(tree.root_node, print_node, class_name=class_name)


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
                    # print(class_name + "." + method_ident)
                    count += 1
    return count


def parse_test_class(filename, class_name):
    tree = parse_file(filename)
    return dfs(tree.root_node, declare_class, class_name=class_name)


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
