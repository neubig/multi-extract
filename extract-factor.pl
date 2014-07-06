#!/usr/bin/perl

use strict;
use warnings;
use utf8;
use Getopt::Long;
use List::Util qw(sum min max shuffle);
binmode STDIN, ":utf8";
binmode STDOUT, ":utf8";
binmode STDERR, ":utf8";

my $ARG = "";
GetOptions(
"arg=s" => \$ARG,
);

if(@ARGV != 1) {
    print STDERR "Usage: $0 FACTOR\n";
    exit 1;
}

while(<STDIN>) {
    chomp;
    my @arr = split(/ \|\|\| /);
    my @cols = split(/ \|COL\| /, $arr[1]);
    $arr[1] = $cols[$ARGV[0]];
    print join(" ||| ", @arr)."\n";
}
