use 5.12.0;
for ('01'..'26') {
    my ($dic) = glob("*$_*.dic");
    say("Processing $dic");
    system("perl a-tsioh_sandbox/recode_utf8.pl $dic | python a-tsioh_sandbox/dic2json.py | perl font/jade-unescape.pl | python a-tsioh_sandbox/rt2pronun.py > json/$_.json");
    # system("perl a-tsioh_sandbox/recode_utf8.pl $dic | python a-tsioh_sandbox/dic2json.py > json/$_.json");
    # system("perl a-tsioh_sandbox/recode_utf8.pl $dic > $_.dic.utf8.txt");
}

