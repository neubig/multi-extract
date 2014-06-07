#!/usr/bin/python3

import itertools
import argparse
import sys
from collections import defaultdict

################### Arguments ###################

# Arguments
parser = argparse.ArgumentParser(description='Extract a synchronous grammar with one or more outputs.')
parser.add_argument('src', type=str, help='The source sentences')
parser.add_argument('trgs', type=str, nargs='+', help='Target sentences, and alignments. The number of arguments must be even, but can have any number.')
parser.add_argument('--max_span', default=15, type=int, help='The maximum overall span to extract')
parser.add_argument('--max_sym_src', default=5, type=int, help='The maximum number of source words')
parser.add_argument('--max_sym_trg', default=999, type=int, help='The maximum number of target words')
parser.add_argument('--max_non_term', default=2, type=int, help='The maximum number of non-terms')
parser.add_argument('--nonterm_consec_src', type=bool, help='Whether it is acceptable for nonterminals to be next to eachother')
# parser.add_argument('--min_words_src', type=int, help='')
# parser.add_argument('--allow_only_unaligned', type=bool, help='')
args = parser.parse_args()

# Sanity check
if len(args.trgs) % 2 != 0:
    raise Exception("Must have even number of target files, one sentence and alignment for each target")

print(args, file=sys.stderr)


################### Functions ###################

# Parsing functions
def parse_words(x):
    return x.strip().split(" ")
def parse_align(x):
    ret = []
    for y in parse_words(x):
        y = y.split("-")
        ret.append((int(y[0]), (int(y[1]))))
    return ret

# Phrase extraction function
#  phrases are in the format [ (src_left, src_right), (trg1_left, trg1_right), ... ]
# align is the list of alignments for the next span to be added
MAX_LEN = 99999
def extract_phrases(phrases, align):
    ret = []
    # Get the closures of all target words and alignments of all source words
    ialigns = defaultdict(lambda: [])
    jclosures = defaultdict(lambda: (MAX_LEN, -1))
    for i, j in align:
        jclosures[j] = (min(i, jclosures[j][0]), max(i, jclosures[j][1]))
        ialigns[i].append(j)    
    # For all source spans, check if they are ok
    for phrase in phrases:
        ok = True
        trg_span = (MAX_LEN, -1)
        for i in range(*phrase[0]):
            for j in ialigns[i]:
                trg_span = (min(trg_span[0], j), max(trg_span[1], j+1))
        if trg_span[0] == MAX_LEN:
            continue
        for j in range(*trg_span):
            if jclosures[j][0] < phrase[0][0] or jclosures[j][1] >= phrase[0][1]:
                ok = False
                break
        if ok:
            phrase.append(trg_span)
            ret.append(phrase)
    return ret

################## Main Program ###################

# Get handles to all files
files = [open(args.src, "r")]
for trg in args.trgs:
    files.append(open(trg, "r"))
    
# Process every line
for strs in zip(*files):
    strs = [x.strip() for x in strs]
    # Parse the values
    words = [parse_words(strs[0])]
    for x in strs[1::2]:
        words.append(parse_words(x))
    aligns = [ parse_align(x) for x in strs[2::2] ]
    # Get non-null alignments
    nonnull = [set([x[0] for xs in aligns for x in xs])]
    for g in aligns:
        nonnull.append(set([x[1] for x in g]))
    # Get the alignable source phrases
    phrases = []
    for i in range(0, len(words[0])):
        for j in range(i+1, min(i+args.max_span,len(words[0])+1)):
            if i in nonnull[0] and j-1 in nonnull[0]:
                phrases.append( [(i,j)] )
    # For each target, add the alignable targets
    for word, g in zip(words[1:], aligns):
        phrases = extract_phrases(phrases, g)
    print(words)
    print(aligns)
    print(nonnull)
    print(phrases)
    for phrase in phrases:
        columns = []
        for word, span in zip(words, phrase):
            columns.append(" ".join(word[span[0]:span[1]]))
        print(" ||| ".join(columns))
    print("")
