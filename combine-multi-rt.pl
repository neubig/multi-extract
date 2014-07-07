#!/usr/bin/perl

use strict;
use warnings;
use utf8;
use Getopt::Long;
use List::Util qw(sum min max shuffle);
binmode STDIN, ":utf8";
binmode STDOUT, ":utf8";
binmode STDERR, ":utf8";

my $LIMIT = "20";
GetOptions(
"limit=i" => \$LIMIT,
);

if((@ARGV == 0) or (@ARGV % 2 != 0)) {
    print STDERR "Usage: $0 SRCTRG_ALL TRGSRC_ALL SRCTRG_0 TRGSRC_0 ...\n";
    exit 1;
}

sub read_until_next {
    my ($handle, $arr) = @_;
    while(<$handle>) {
        chomp;
        my ($src, $trg, $feat) = split(/ \|\|\| /);
        if((@$arr == 0) or ($arr->[0]->[0] eq $src)) {
            push @$arr, [$src, $trg, $feat];
        } else {
            return [ [$src, $trg, $feat] ];
        }
    }
    return 0;
}

my @handles = map { open_or_zcat($_) } @ARGV;

my @currs = map { [] } @ARGV;

while($currs[0]) {
    my @nexts;
    foreach my $i (0 .. $#currs) {
        push @nexts, read_until_next($handles[$i], $currs[$i]);
    }
    # Index the first value
    my @out = @{$currs[0]};
    my %idx;
    foreach my $i (0 .. $#out) {
        my ($src, $trg, $feat) = @{$out[$i]};
        my @cols = split(/ \|COL\| /, $trg);
        $idx{"0 $trg"} = [] if not $idx{"0 $trg"};
        push @{$idx{"0 $trg"}}, $i;
        foreach my $col (0 .. $#cols) {
            my $id = "".($col+1)." $cols[$col]";
            $idx{$id} = [] if not $idx{$id};
            push @{$idx{$id}}, $i;
        }
    }
    # Add the features
    foreach my $file (1 .. $#currs) {
        my $id = int(($file)/2);
        # print "FILE: $file -> ID: $id\n";
        foreach my $cols (@{$currs[$file]}) {
            foreach my $line (@{$idx{"$id $cols->[1]"}}) {
                $out[$line]->[2] .= " $cols->[2]";
            }
        }
    }
    # Filter the features and calculate the trimming score
    my @sorted;
    foreach my $cols (@out) {
        $cols->[2] = join(" ", grep(!/^(w=|\d+p=|\d*lfreq)/, split(/ /, $cols->[2])));
        my $str = join(" ||| ",@{$cols});
        $str =~ / egfp=([^ ]+)/ or die "No e given f probability in $str";
        @sorted = [$1, $str];
    }
    @sorted = sort { $b->[0] <=> $a->[0] } @sorted;
    # Print the top n
    my $done = 0;
    for(@sorted) {
        last if $done >= $LIMIT;
        print "$_->[1]\n";
        $done += 1;
    }
    # Index the array
    @currs = @nexts;
}

####################### utilities ######################
sub open_or_zcat {
  my $fn = shift;
  my $read = $fn;
  $fn = $fn.".gz" if ! -e $fn && -e $fn.".gz";
  $fn = $fn.".bz2" if ! -e $fn && -e $fn.".bz2";
  if ($fn =~ /\.bz2$/) {
      $read = "bzcat $fn|";
  } elsif ($fn =~ /\.gz$/) {
      $read = "gzip -cd $fn|";
  }
  my $hdl;
  open($hdl,$read) or die "Can't read $fn ($read)";
  binmode $hdl, ":utf8";
  return $hdl;
}
