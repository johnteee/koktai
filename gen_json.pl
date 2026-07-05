use 5.12.0;
for ('01'..'26') {
    my ($dic) = glob("*$_*.dic");
    say("Processing $dic");
    # koktai-dic/2：造字解碼併入 dic2json.py（不再依賴 jade-unescape.pl/CPAN）
    system("perl a-tsioh_sandbox/recode_utf8.pl $dic | python3 a-tsioh_sandbox/dic2json.py | python3 a-tsioh_sandbox/rt2pronun.py > json/$_.json");
}

