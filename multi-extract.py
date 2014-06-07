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
parser.add_argument('--min_src_interceding', default=1, type=int, help='Minimum number of terminals between non-terms in the source')
# parser.add_argument('--min_words_src', type=int, help='')
# parser.add_argument('--allow_only_unaligned', type=bool, help='')
args = parser.parse_args()

# Sanity check
if len(args.trgs) % 2 != 0:
    raise Exception("Must have even number of target files, one sentence and alignment for each target")
num_trgs = int(len(args.trgs)/2)

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

# Return true if the rule is OK, false if not
max_sym = ((args.max_sym_src,) + (args.max_sym_trg,)*num_trgs)
def rule_filter(rule):
    # Is the number of symbols OK?
    lens = [rule[0][i][1]-rule[0][i][0]-sum([y[i][1]-y[i][0] for y in rule[1:]]) for i in range(len(rule[0]))]
    for i, syms in enumerate(lens):
        if syms > max_sym[i]:
            return 0
    return 1

# Take phrases and make hiero phrases
def abstract_phrases(phrases):
    # Index phrases to use as holes (use all phrases for now)
    holes = phrases
    hole_idxs = defaultdict(lambda: [])
    for idx, (i_left, i_right) in enumerate([x[0] for x in holes]):
        hole_idxs[i_left].append( (i_right, idx) )
    # Create all non-abstracted phrases
    ret = []
    cnt = []
    for phrase in phrases:
        # Add each phrase
        idx = idx_start = len(ret)
        ret.append( (phrase,) )
        while idx < len(ret):
            curr = ret[idx]
            idx += 1
            # Skip if we already have enough non-terms
            if len(curr) > args.max_non_term:
                continue
            # Start checking the remaining holes either at
            # the beginning of the phrase, or the end of the last hole
            i_start = curr[0][0][0] if len(curr) == 1 else curr[-1][0][1]+args.min_src_interceding
            for i_left in range(i_start, curr[0][0][1]):
                for i_right, i_idx in hole_idxs[i_left]:
                    # If we don't exceed the right side or cover the whole phrase
                    if i_right <= curr[0][0][1] and curr[0][0] != holes[i_idx][0]:
                        ret.append( curr + (holes[i_idx],) )
        # Add the cnt divided by the number of elements
        num_elem = idx-idx_start
        cnt.extend( (1.0/num_elem,)*num_elem )
    return [x for x in zip(ret, cnt) if rule_filter(x[0])]

# Create a single string of abstracted rules
def create_phrase_string(words, span, holes):
    # print("span: %r" % str(span))
    # print("holes: %r" % str(holes))
    # Add the words and delete the holes
    prelim = words[span[0]:span[1]]
    for idx, hole_span in enumerate(holes):
        for i in range(hole_span[0]-span[0], hole_span[1]-span[0]):
            prelim[i] = idx
    # Add quotes for words and add holes only once
    hole_done = set()
    ret = []
    for pre in prelim:
        if type(pre) is str:
            ret.append("\"%s\"" % pre)
        elif not pre in hole_done:
            ret.append("x%d" % pre)
            hole_done.add(pre)
    return " ".join(ret)

# Convert a full rule into a travatar-style representation
def create_rule_string(words, phrase, count):
    span = phrase[0]
    holes = phrase[1:]
    strs = [ create_phrase_string(words[x], span[x], [y[x] for y in holes]) for x in range(0, len(words)) ]
    return "%s ||| %s ||| %f" % (strs[0], " |COL| ".join(strs[1:]), count)

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
    # Abstract phrases
    abstracted = abstract_phrases(phrases)
    for hiero, hcount in abstracted:
        print(create_rule_string(words, hiero, hcount))
