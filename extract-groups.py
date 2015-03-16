#!/usr/bin/python3

import sys
import re
import itertools
from collections import defaultdict

# A dictionary with
#  src: spans[file_name][0][sentence] = assigned_span
#  trg: spans[file_name][1][lang][sentence] = english
spans = defaultdict(lambda: (defaultdict(lambda: [9999999, -1]), defaultdict(lambda: []), defaultdict(lambda: 99999999)))

for xmlname in sys.argv[1:]:
    print("Reading file %s" % xmlname, file=sys.stderr)
    # Match and open the xml file
    match = re.search(r"en-(..).xml", xmlname)
    if match:
        src_idx = 0
        lang = match.group(1)
    else:
        match = re.search(r"(..)-en.xml", xmlname)
        if not match:
            raise Exception("Didn't match %s"%xmlname)
        src_idx = 1
        lang = match.group(1)
    xmlfile = open(xmlname, "r")
    currname = ""
    lineno = 0
    # Grab the spans from every line
    for line in xmlfile:
        match = re.match(r" <linkGrp.*toDoc=\"(.*)\" fromDoc=\"(.*)\"", line)
        if match:
            currname = match.group(2-src_idx)
        else:
            match = re.match(r"<link certainty=\"(.*)\" xtargets=\"([0-9 ]*);([0-9 ]*)\"", line)
            if match and match.group(src_idx+2):
                # Find the src
                src_arr = [int(x) for x in match.group(src_idx+2).split(" ")]
                src_min = min(src_arr)
                src_max = max(src_arr)
                curr_spans0, curr_spans1, confs = spans[currname]
                conf = float(match.group(1))
                for src in src_arr:
                    confs[src] = min(confs[src], conf)
                    curr_spans0[src] = (min(src_min, curr_spans0[src][0]),
                                        max(src_max, curr_spans0[src][1]))
                if match.group(3-src_idx):
                    # Create the target range
                    trg_arr = [int(x) for x in match.group(3-src_idx).split(" ")]
                    trg_range = (min(trg_arr), max(trg_arr))
                    curr_spans1[lang].append( (trg_range, src_min) )
        # Print progress
        lineno += 1
        if lineno % 1000000 == 0:
            sys.stderr.write("*")
            sys.stderr.flush()
        elif lineno % 100000 == 0:
            sys.stderr.write(".")
            sys.stderr.flush()
    print("DONE!", file=sys.stderr)


# Given a dictionary of sentences and the spans, expand the spans until they no
# longer contradict
def expand_links(links):
    span_len = -1
    next_len = sum([y[1]-y[0] for x, y in links.items()])
    while next_len != span_len:
        span_len = next_len
        for x, y in links.items():
            my_spans = [links[x] for x in range(y[0], y[1]+1) if x in links]
            links[x] = (min([x[0] for x in my_spans]),
                        max([x[1] for x in my_spans]))
        next_len = sum([y[1]-y[0] for x, y in links.items()])


print("Found %d files! Printing file by file." % len(spans), file=sys.stderr)
# Create the mapping
for filename, (src_links, trg_links, confs) in spans.items():
    # Expand the links
    expand_links(src_links)
    # The things we want to make
    langs = ["en"]
    block_ranges = []
    # Expand the block map
    block = 0
    block_map = {}
    my_ranges = {}
    my_confs = {}
    for spans in sorted(set(src_links.values())):
        my_ranges[block] = spans
        conf = 999999999
        for src in range(spans[0], spans[1]+1):
            block_map[src] = block
            conf = min(conf, confs[src])
        my_confs[block] = conf
        block += 1

    block_ranges.append(my_ranges)
    # Create the languages
    for lang, trg_dict in trg_links.items():
        my_ranges = {}
        langs.append(lang)
        for trg_range, src in trg_dict:
            my_ranges[block_map[src]] = trg_range
        block_ranges.append(my_ranges)
    print(filename)
    print("\t".join(langs))
    for i in range(len(block_ranges[0])):
        print("%s ||| %f" % ("\t".join([("%d-%d" % (x[i][0], x[i][1]) if (i in x) else "") for x in block_ranges]), my_confs[i]))
    print("")
