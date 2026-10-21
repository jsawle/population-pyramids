import sys
t = open(sys.argv[1], encoding="utf-8").read()
d = open(sys.argv[2], encoding="utf-8").read().replace("</", "<\\/")
assert t.count("/*__DATA__*/") == 1
open(sys.argv[3], "w", encoding="utf-8").write(t.replace("/*__DATA__*/", d))
