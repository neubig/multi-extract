#!/usr/bin/perl

use strict;
use warnings;
use utf8;
use Getopt::Long;
use List::Util qw(sum min max shuffle);
binmode STDIN, ":utf8";
binmode STDOUT, ":utf8";
binmode STDERR, ":utf8";

my $THREADS=2;
my $LMSIZE="10000000";
my $TMSIZE="00100000";
GetOptions(
"threads=s" => \$THREADS,
);

if(@ARGV == 0) {
    print STDERR "Usage: $0 ar zh ...\n";
    exit 1;
}

my $HOME = "/home/is/neubig";
my $MULTDIR="$HOME/work/multi-extract";
my $TRAVDIR="$HOME/work/travatar";
my $GIZADIR="$HOME/usr/local/giza-pp";
my $WD=`pwd`; chomp $WD;
my $SRC="en";
my @trgs = @ARGV;

#################### Rule extraction ##############################

# Check to make sure the target files and alignments exists
my @files = ("tok/train-$TMSIZE.$SRC");
my @standmod;
for(@trgs) {
    push @files, "tok/train-$TMSIZE.$_";
    push @standmod, "standard-model/$SRC$_-lm$LMSIZE-tm$TMSIZE";
    push @files, "$standmod[-1]/align/align.txt";
}
for(@files) { -e $_ or die "Could not find file $_\n"; }

my $ID = "$SRC".join("", @trgs)."-lm$LMSIZE-tm$TMSIZE";

# Create the output directory
(not -e "multi-model/$ID") or die "multi-model/$ID already exists";

# Perform rule extraction
safesystem("mkdir -p multi-model/$ID/model") or die;
safesystem("$MULTDIR/multi-extract.py @files | gzip > multi-model/$ID/model/extract.gz") or die;

# Score the table as a whole with no lexical weighting
my $cmd1 = "zcat multi-model/$ID/model/extract.gz | env LC_ALL=C sort | $TRAVDIR/script/train/score-t2s.pl --cond-prefix=egf --joint | env LC_ALL=C sort | gzip > multi-model/$ID/model/rule-table.src-trg.all.gz";
my $cmd2 = "zcat multi-model/$ID/model/extract.gz | $TRAVDIR/script/train/reverse-rt.pl | env LC_ALL=C sort | $TRAVDIR/script/train/score-t2s.pl --cond-prefix=fge | $TRAVDIR/script/train/reverse-rt.pl | env LC_ALL=C sort | gzip > multi-model/$ID/model/rule-table.trg-src.all.gz";
run_two($cmd1, $cmd2);

# Score each factor of the table with conditional probabilities and lexical
foreach my $factnum (0 .. $#trgs) {
    my $trg = $trgs[$factnum];
    $cmd1 = "zcat multi-model/$ID/model/extract.gz | $MULTDIR/script/extract-factor.pl $factnum | env LC_ALL=C sort | $TRAVDIR/script/train/score-t2s.pl --lex-prob-file=$standmod[$factnum]/lex/trg_given_src.lex --prefix=$factnum --cond-prefix=egf --joint | env LC_ALL=C sort | gzip > multi-model/$ID/model/rule-table.src-trg.$factnum.gz";
    $cmd2 = "zcat multi-model/$ID/model/extract.gz | $MULTDIR/script/extract-factor.pl $factnum | $TRAVDIR/script/train/reverse-rt.pl | env LC_ALL=C sort | $TRAVDIR/script/train/score-t2s.pl --lex-prob-file=$standmod[$factnum]/lex/src_given_trg.lex --prefix=$factnum --cond-prefix=fge | $TRAVDIR/script/train/reverse-rt.pl | env LC_ALL=C sort | gzip > multi-model/$ID/model/rule-table.trg-src.$factnum.gz";
    run_two($cmd1, $cmd2);
}

# Create the multi-output phrase table
my @tables;
for my $factnum ("all", 0 .. $#trgs) {
    for my $dir (qw(src-trg trg-src)) {
        push @tables, "multi-model/$ID/model/rule-table.$dir.$factnum.gz";
    }
}
safesystem("$MULTDIR/script/combine-multi-rt.pl @tables | gzip > multi-model/$ID/model/rule-table.gz");

# Create the glue rules
my $gfile = "$WD/multi-model/$ID/model/glue-rules";
open GFILE, ">:utf8", $gfile or die "Couldn't open $gfile\n";
print GFILE "x0:X @ S ||| "     .join(" |COL| ", map { "x0:X @ S"      } (0 .. $#trgs))." ||| \n";
print GFILE "x0:S x1:X @ S ||| ".join(" |COL| ", map { "x0:S x1:X @ S" } (0 .. $#trgs))." ||| glue=1\n";
close GFILE;

# Create the config file
my $TINI_FILE = "$WD/multi-model/$ID/model/travatar.ini";
my $TM_FILES   = "$WD/multi-model/$ID/model/rule-table.gz\n$WD/multi-model/$ID/model/glue-rules";
my $LM_FILES   = join("\n", map { "$WD/lm/$trgs[$_]-lm$LMSIZE.blm|factor=$_,lm_feat=${_}lm,lm_unk_feat=${_}lmunk" } (0 .. $#trgs));
open TINI, ">:utf8", $TINI_FILE or die "Couldn't open $TINI_FILE\n";
print TINI "[tm_file]\n$TM_FILES\n\n";
print TINI "[lm_file]\n$LM_FILES\n\n";
print TINI "[in_format]\nword\n\n";
print TINI "[tm_storage]\nfsm\n\n";
print TINI "[search]\ncp\n\n";
print TINI "[trg_factors]\n".@trgs."\n\n";
print TINI "[hiero_span_limit]\n20\n1000\n\n";

# Default values for the weights
my $weights = "0egfp=0.05\n0egfl=0.05\n0fgep=0.05\n0fgel=0.05\n0lm=0.3\n0w=0.3\np=-0.15\nunk=-1\nlfreq=0.05\n";
print TINI "[weight_vals]\n$weights\n";
close TINI;
print "Finished training! You can find the configuation file in:\n$TINI_FILE\n";


#################### Utility functions ############################

# Adapted from Moses's train-model.perl
sub safesystem {
  print STDERR "Executing: @_\n";
  system(@_);
  if ($? == -1) {
      print STDERR "ERROR: Failed to execute: @_\n  $!\n";
      exit(1);
  }
  elsif ($? & 127) {
      printf STDERR "ERROR: Execution of: @_\n  died with signal %d, %s coredump\n",
          ($? & 127),  ($? & 128) ? 'with' : 'without';
      exit(1);
  }
  else {
    my $exitcode = $? >> 8;
    print STDERR "Exit code: $exitcode\n" if $exitcode;
    return ! $exitcode;
  }
}

sub run_two {
    @_ == 2 or die "run_two handles two commands, got @_\n";
    my ($CMD1, $CMD2) = @_;
    if($THREADS > 1) {
	    my $pid = fork();
	    die "ERROR: couldn't fork" unless defined $pid;
        if(!$pid) {
            safesystem("$CMD1") or die;
            exit 0;
        } else {
            safesystem("$CMD2") or die;
            waitpid($pid, 0);
        }
    } else {
        safesystem("$CMD1") or die;
        safesystem("$CMD2") or die;
    }
}
