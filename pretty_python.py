#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This script checks and fixes formatting in python scripts:
# - Checks and fixes python shebang to /usr/bin/env python
# - Checks and fixes python coding to utf-8
# - Checks and fixes PEP8 formatting
#
# Requires autopep8. Install it with:
# pip install --upgrade argparse autopep8

import sys
import re
import os
import io
import collections
from subprocess import Popen, PIPE

CR = '\r'
LF = '\n'
CRLF = '\r\n'

WIN32 = sys.platform == 'win32'
SHEBANG_PATTERN = re.compile('#\!')
CORRECT_SHEBANG_PATTERN = re.compile('#\!/usr/bin/env\s+python\s*$')
CORRECT_CODING_LINE = re.compile('#!/usr/bin/env python')

CODING_PATTERN = re.compile('coding[:=]\s*[-\w]+')
CORRECT_CODING_PATTERN = re.compile('coding[=:]\s*utf\-8')
CORRECT_CODING_LINE = '# -*- coding: utf-8 -*-'

# Configuration
PEP8_CHECKER_COMMON_CMD = "autopep8 --recursive --aggressive --aggressive --max-line-length 99"
PEP8_CHECK_CMD = PEP8_CHECKER_COMMON_CMD + " --diff"
PEP8_FIX_CMD = PEP8_CHECKER_COMMON_CMD + " --in-place --verbose"


def is_python_file(filename):
    return filename.endswith('.py')


def fix_line_endings(lines, newline):
    return [line.rstrip('\n\r') + newline for line in lines]


def detect_newline(lines):
    """Detect newline type by using the most frequently used newline type"""
    counter = collections.defaultdict(int)
    for line in lines:
        if line.endswith(CRLF):
            counter[CRLF] += 1
        elif line.endswith(CR):
            counter[CR] += 1
        elif line.endswith(LF):
            counter[LF] += 1

    if not counter:
        return LF
    return sorted(counter, key=counter.get, reverse=True)[0]


def write_file(filename, lines, newline):
    fixed_content = ''.join(fix_line_endings(lines, newline))
    fp = open(filename, 'w')
    fp.write(fixed_content)
    fp.close()


def is_file_ok(filename):
    if os.path.basename(filename).startswith('.'):
        return False
    if not os.path.isdir(filename) and not is_python_file(filename):
        return False
    return True


def recurse_dir(dir):
    """Yield filenames."""
    filenames = [dir]
    while filenames:
        name = filenames.pop(0)
        if os.path.isdir(name):
            for root, directories, children in os.walk(name):
                filenames += [os.path.join(root, f) for f in children
                              if is_file_ok(os.path.join(root, f))]
        else:
            yield name


def check_pep8(dirs):
    cmd = "%s %s" % (PEP8_CHECK_CMD, " ".join(dirs))
    if WIN32:
        cmd = 'python ' + cmd
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    if p.returncode == 0:
        if out:
            print >> sys.stderr, out
            return False
    else:
        print >> sys.stderr, "Error checking code formatting\n%s" % err
        return False
    return True


def check_shebang(dirs):
    success = True
    for dir in dirs:
        for filename in recurse_dir(dir):
            lines = io.open(filename, encoding='utf-8', mode='rt').readlines()
            if len(lines) < 1 or CORRECT_SHEBANG_PATTERN.match(lines[0]) is None:
                success = False
                print >> sys.stderr, 'Invalid shebang header in ' + filename

    return success


def check_coding(dirs):
    success = True
    for dir in dirs:
        for filename in recurse_dir(dir):
            lines = io.open(filename, encoding='utf-8', mode='rt').readlines()
            if len(lines) >= 2 and CORRECT_CODING_PATTERN.search(lines[1]) is not None:
                continue
            if len(lines) >= 1 and CORRECT_CODING_PATTERN.search(lines[0]) is not None:
                continue
            success = False
            print >> sys.stderr, 'Invalid coding header in ' + filename

    return success


def fix_pep8(dirs):
    cmd = "%s %s" % (PEP8_FIX_CMD, " ".join(dirs))
    if WIN32:
        cmd = 'python ' + cmd
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    if p.returncode != 0:
        print >> sys.stderr, "Error checking code formatting\n%s" % err
        return False
    if out:
        print(out)
    return True


def fix_shebang(dirs):
    for dir in dirs:
        for filename in recurse_dir(dir):
            lines = io.open(filename, encoding='utf-8', mode='rt').readlines()
            original_newline = detect_newline(lines)

            if len(lines) == 0 or SHEBANG_PATTERN.match(lines[0]) is None:
                # no shebang at all, adding it
                lines.insert(0, CORRECT_CODING_LINE)
            elif CORRECT_SHEBANG_PATTERN.match(lines[0]) is None:
                # shebang is there but it is nok, fixing it
                lines[0] = CORRECT_CODING_LINE
            else:
                continue

            print('Fixing shebang of ' + filename)
            write_file(filename, lines, original_newline)

    return True


def fix_coding(dirs):
    "PRE: correct shebang is already present"
    for dir in dirs:
        for filename in recurse_dir(dir):
            lines = io.open(filename, encoding='utf-8', mode='rt').readlines()
            original_newline = detect_newline(lines)

            assert(CORRECT_SHEBANG_PATTERN.match(lines[0]))

            if len(lines) == 1:
                # no coding because the first line is shebang, adding coding
                lines.append(CORRECT_CODING_LINE)
            elif len(lines) >= 2:
                if CORRECT_CODING_PATTERN.search(lines[1]) is not None:
                    continue
                if CODING_PATTERN.search(lines[1]) is None:
                    # no coding at all, adding it
                    lines.insert(1, CORRECT_CODING_LINE)
                else:
                    # coding is there but it is nok, fixing it
                    lines[1] = CORRECT_CODING_LINE

            print('Fixing coding of ' + filename)
            write_file(filename, lines, original_newline)

    return True


if __name__ == "__main__":
    # If called directly recursively check/fix scripts in the current dir
    dirs = ['./']

    # Check
    if len(sys.argv) == 1:
        success = check_shebang(dirs)
        success = check_coding(dirs) and success
        success = check_pep8(dirs) and success
        sys.exit(0 if success else 1)

    # Fix
    elif len(sys.argv) == 2 and sys.argv[1] == "--fix":
        success = fix_shebang(dirs) and fix_coding(dirs) and fix_pep8(dirs)
        sys.exit(0 if success else 1)

    else:
        print("Usage: %s [--fix]")
        sys.exit(1)
