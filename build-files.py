#!/usr/bin/python3

import sys
import re
import gzip

input_prefix = sys.argv[1]
output_prefix = sys.argv[2]
langs = sys.argv[3:]
lang_map = {}
for idx, lang in enumerate(langs):
    lang_map[lang] = idx
files = []
for x in langs:
    files.append(open("%s%s.txt" % (output_prefix, x), "w"))

# <s id="1">
#  <chunk type="NP" id="c-1">
#   <w head="2" hun="NNP" tree="NP" pos="JJ" id="w1.1" deprel="nn">Fifty-sixth</w>
#   <w head="0" hun="NN" tree="NN" lem="session" pos="NN" id="w1.2" deprel="null">session</w>
#  </chunk>
# </s></p><p n="2">
# <s id="2">
#  <chunk type="NP" id="c-1">
#   <w head="0" hun="NN" tree="NN" lem="item" pos="NNP" id="w2.1" deprel="null">Item</w>
#   <w head="3" hun="CD" tree="CD" lem="@card@" pos="CD" id="w2.2" deprel="number">11</w>
#  </chunk>
def read_xml_lines(filename):
    xml_file = gzip.open(filename, "rb")
    words = []
    for line in xml_file:
        line = line.decode().strip()
        match = re.search(r"<s ", line)
        if match:
            words.append([])
        else:
            match = re.search(r">([^>]+)<\/w>", line)
            if match:
                word = match.group(1)
                if(len(words) == 0):
                    print("Empty word in file %s\n%s" % (filename, line))
                else:
                    words[-1].append(word)
    return [" ".join(x) for x in words]

processed_files = total_files = 0
for line in sys.stdin:
    total_files += 1
    if total_files % 10 == 0:
        sys.stdout.write("*" if total_files % 100 == 0 else ".")
        if total_files % 500 == 0: print(" %d" % total_files)
        else: sys.stdout.flush()

    match = re.match(r"en\/(.*)", line.strip())
    if not match: raise Exception("bad file name: %s" % line)
    path = match.group(1)
    my_langs = sys.stdin.readline().strip().split("\t")
    # Check if all languages are present for this file
    skip = False
    for idx, lang in enumerate(langs):
        if not lang in my_langs:
            skip = True
            break
    # Read in the rest
    ranges = [[] for x in langs]
    while True:
        line = sys.stdin.readline().strip()
        if not line: break
        idvals = line.split("\t")
        while len(idvals) < len(my_langs): idvals.append("")
        for idx, val in enumerate(idvals):
            if my_langs[idx] in lang_map:
                ranges[lang_map[my_langs[idx]]].append(val)
    if skip:
        continue
    processed_files += 1
    # Read the lines of each file
    for idx, lang in enumerate(langs):
        doc_lines = read_xml_lines("%s/%s/%s" % (input_prefix, lang, path))
        for my_range in ranges[idx]:
            if not my_range:
                print("", file=files[idx])
            else:
                span = [int(x) for x in my_range.split("-")]
                print(" ".join(doc_lines[span[0]-1:span[1]]), file=files[idx])

print("DONE!")
print ("%s/%s files processed" % (processed_files, total_files), file=sys.stderr)
