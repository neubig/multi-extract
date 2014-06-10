#!/usr/bin/python

import unittest
import RuleExtractor

class TestRuleExtractor(unittest.TestCase):

    def setUp(self):
        self.default = RuleExtractor.RuleExtractor()
        # create a sentence
        self.taro_f = ["kare", "wa", "taro", "to", "mo", "iwareru"]
        self.taro_e = ["he", "is", "also", "called", "taro"]
        self.taro_a = [(0,0), (2,4), (3,1), (3,3), (4,2), (5,1), (5,3)]

    def test_parse_words(self):
        in_str = " a  b c "
        exp_sent = ["a", "b", "c"]
        act_sent = self.default.parse_words(in_str)
        self.assertEqual(act_sent, exp_sent)

    def test_parse_align(self):
        in_str = " 0-1-P  1-2-S 0-3 "
        exp_sent = [(0,1), (1,2), (0,3)]
        act_sent = self.default.parse_align(in_str)
        self.assertEqual(act_sent, exp_sent)

    def test_nonnull(self):
        exp_nonnull = [set((0,2,3,4,5)), set((0,1,2,3,4))]
        act_nonnull = self.default.create_nonnull( [self.taro_a] )
        self.assertEqual(act_nonnull, exp_nonnull)

    def test_minimal_srcs(self):
        exp_minimal = [[(0,1)], [(0,3)], [(0,4)], [(0,5)], [(0,6)], [(2,3)], [(2,4)], [(2,5)], [(2,6)], [(3,4)], [(3,5)], [(3,6)], [(4,5)], [(4,6)], [(5,6)]]
        act_minimal = self.default.create_minimal_srcs(set((0,2,3,4,5)), 6)
        self.assertEqual(act_minimal, exp_minimal)

    def test_extract_phrases(self):
        candidates = self.default.create_minimal_srcs(set((0,2,3,4,5)), 6)
        exp_phrases = [[(0,1), (0,1)], [(0,6), (0,5)], [(2,3), (4,5)], [(2,6), (1,5)], [(3,6), (1,4)], [(4,5), (2,3)]]
        act_phrases = self.default.extract_phrases(candidates, self.taro_a)
        self.assertEqual(act_phrases, exp_phrases)
    
    def test_phrase_string(self):
        holes = [(2,4), (1,2)]
        exp_phrase = "\"he\" x1 x0 \"taro\""
        act_phrase = self.default.create_phrase_string(self.taro_e, (0,5), holes)
        self.assertEqual(act_phrase, exp_phrase)

    def test_extend_range(self):
        nonnull = set( (1,) )
        exp_extend = [(2,4), (2,5), (2,6), (3,4), (3,5), (3,6)]
        act_extend = list(self.default.extend_range((3,4), nonnull, 6))
        self.assertEqual(act_extend, exp_extend)

    def test_add_nulls(self):
        holes = [[(0,1), (0,1)], [(0,6), (0,5)], [(2,3), (4,5)], [(2,6), (1,5)], [(3,6), (1,4)], [(4,5), (2,3)]]
        exp_phrases = [[(0,1), (0,1)], [(0,2), (0,1)], [(0,6), (0,5)], [(1,3), (4,5)], [(2,3), (4,5)], [(1,6), (1,5)], [(2,6), (1,5)], [(3,6), (1,4)], [(4,5), (2,3)]]
        act_phrases = self.default.add_nulls([self.taro_f, self.taro_e], holes, [set((0,2,3,4,5)), set((0,1,2,3,4))])
        self.assertEqual(act_phrases, exp_phrases)

if __name__ == '__main__':
    unittest.main()
