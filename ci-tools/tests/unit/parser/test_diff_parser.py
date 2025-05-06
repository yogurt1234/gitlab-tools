# tests/unit/test_diff_parser.py

from modules.gitlab.diff_parser import GitLabDiffParser, GitLocalDiffParser

# Sample diff text for parse_hunk_header
SAMPLE_DIFF = """
@@ -1,3 +1,4 @@
 line1
+added1
 line2
 line3
@@ -10 +12,2 @@
-context
+new1
+new2
 context2
"""


def test_parse_hunk_header_simple():
    parser = GitLabDiffParser()
    # Access the protected method via instance
    changed = parser.parse_hunk_header(SAMPLE_DIFF)
    # From first hunk: added1 at new line 2 -> line number 2
    # second hunk: new1 at line 12, new2 at 13
    assert changed == {2, 12, 13}


def test_gitlab_diff_parser_parse_filters_and_includes():
    gp = GitLabDiffParser()
    change_context = {
        "diff_refs": {"base_sha": "b1", "start_sha": "s1", "head_sha": "h1"},
        "changes": [
            # include with non-empty hunk
            {"old_path": "a.txt", "new_path": "a.txt", "diff": "@@ -0 +1 @@\n+line"},
            # include but no additions => skip
            {"old_path": "b.txt", "new_path": "b.txt", "diff": "@@ -1 +1 @@\n line"},
            # skip if diff missing
            {"old_path": "c.txt", "new_path": "c.txt", "diff": None},
            # skip if new_path missing
            {"old_path": "d.txt", "new_path": "", "diff": "@@ -0 +1 @@\n+x"}
        ]
    }
    result = gp.parse(change_context)
    # diff_refs keys
    assert result['base_sha'] == 'b1'
    assert result['start_sha'] == 's1'
    assert result['head_sha'] == 'h1'
    # Only a.txt should be included with changed_lines {1}
    assert 'a.txt' in result
    info = result['a.txt']
    assert info['old_path'] == 'a.txt'
    assert info['new_path'] == 'a.txt'
    assert info['changed_lines'] == {1}
    # b.txt should not appear
    assert 'b.txt' not in result


def test_gitlocal_diff_parser_basic():
    text = (
        "diff --git a/foo.txt b/foo.txt\n"
        "@@ -1,2 +1,3 @@\n"
        " line1\n"
        "+added1\n"
        " line2\n"
        "@@ -10 +12 @@\n"
        "-removed\n"
        "+new2\n"
    )
    lp = GitLocalDiffParser()
    parsed = lp.parse(text)
    # Should include foo.txt with changed_lines {2,12}
    assert 'foo.txt' in parsed
    cl = parsed['foo.txt']['changed_lines']
    assert cl == {2, 12}


def test_parse_hunk_header_no_hunks():
    # GitLabDiffParser の parse_hunk_header を使う
    from modules.gitlab.diff_parser import GitLabDiffParser
    parser = GitLabDiffParser()
    empty = parser.parse_hunk_header("no hunks here")
    assert empty == set()
