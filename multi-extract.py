#!/usr/bin/python3

import itertools
import argparse
import sys

import RuleExtractor

################### Arguments ###################

# Arguments
parser = argparse.ArgumentParser(description='Extract a synchronous grammar with one or more outputs.')
parser.add_argument('src', type=str, help='The source sentences')
parser.add_argument('trgs', type=str, nargs='+', help='Target sentences, and alignments. The number of arguments must be even, but can have any number.')
parser.add_argument('--max_span', default=15, type=int, help='The maximum overall span to extract')
parser.add_argument('--max_sym_src', default=5, type=int, help='The maximum number of source words')
parser.add_argument('--max_sym_trg', default=999, type=int, help='The maximum number of target words')
parser.add_argument('--max_nonterm', default=2, type=int, help='The maximum number of non-terms')
parser.add_argument('--min_src_interceding', default=1, type=int, help='Minimum number of terminals between non-terms in the source')
# parser.add_argument('--min_words_src', type=int, help='')
# parser.add_argument('--allow_only_unaligned', type=bool, help='')
args = parser.parse_args()

# Sanity check
if len(args.trgs) % 2 != 0:
    raise Exception("Must have even number of target files, one sentence and alignment for each target")
num_trgs = int(len(args.trgs)/2)

print(args, file=sys.stderr)

################## Main Program ###################

# Get handles to all files
files = [open(args.src, "r")]
for trg in args.trgs:
    files.append(open(trg, "r"))

# Create the extractor
extractor = RuleExtractor.RuleExtractor(max_span=args.max_span, max_sym_src=args.max_sym_src, max_sym_trg=args.max_sym_trg, max_nonterm=args.max_nonterm, min_src_interceding=args.min_src_interceding, num_trgs=num_trgs)

# Process every line
for strs in zip(*files):
    strs = [x.strip() for x in strs]
    # Parse the values
    words = [extractor.parse_words(strs[0])]
    for x in strs[1::2]:
        words.append(extractor.parse_words(x))
    aligns = [ extractor.parse_align(x) for x in strs[2::2] ]
    hiero_rules = extractor.create_hiero_rules(words, aligns)
    for hiero, hcount in hiero_rules:
        print(extractor.create_rule_string(words, hiero, hcount))
