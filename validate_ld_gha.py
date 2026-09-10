# -*- coding: utf-8 -*-
"""在 GitHub Actions runner 上对 novel.jimshang.com 的 16 页 JSON-LD 做 validator.schema.org 官方校验。"""
import json, re, sys, time, urllib.request, urllib.parse

PAGES = ["/", "/filter-era/", "/filter-era/novel.html", "/filter-era/outline.html",
         "/filter-era/characters.html", "/filter-era/world.html",
         "/karma-bureau/", "/karma-bureau/novel.html", "/karma-bureau/outline.html",
         "/karma-bureau/characters.html", "/karma-bureau/world.html",
         "/blackbox/", "/blackbox/novel.html", "/blackbox/outline.html",
         "/blackbox/characters.html", "/blackbox/world.html"]
SITE = "https://novel.jimshang.com"
OUT = "ld_validation.json"


def post(snippet):
    data = urllib.parse.urlencode({"html": snippet}).encode()
    req = urllib.request.Request("https://validator.schema.org/validate", data=data,
                                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
                                          "Accept": "application/json, text/plain, */*",
                                          "Origin": "https://validator.schema.org",
                                          "Referer": "https://validator.schema.org/"})
    r = urllib.request.urlopen(req, timeout=90)
    raw = r.read().decode("utf-8", "ignore")
    if not raw.startswith(")]}'"):
        raise RuntimeError("非预期响应（疑似验证码页）: " + raw[:120])
    return json.loads(raw.split("\n", 1)[1])


def fetch(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
                                  timeout=30).read().decode("utf-8", "ignore")


# 0) 探通
for i in range(5):
    try:
        post('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Book","name":"probe"}</script>')
        print("validator reachable (probe %d)" % (i + 1), flush=True)
        break
    except Exception as e:
        print("probe failed: %s" % e, flush=True)
        if i == 4:
            print("GIVEUP"); sys.exit(1)
        time.sleep(20)

out = []
for p in PAGES:
    u = SITE + p
    h = fetch(u)
    lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
    rec = {"url": u, "blocks": len(lds), "errors": [], "warnings": [], "ok": True}
    for b in lds:
        snippet = '<script type="application/ld+json">%s</script>' % b
        try:
            j = post(snippet)
        except Exception as e:
            rec["ok"] = False
            rec["errors"].append("validator-call-failed: %s" % e)
            continue
        rec["errors"] += [e.get("message") if isinstance(e, dict) else str(e)
                          for e in (j.get("topLevelErrors") or [])]
        rec["errors"] += [e for e in (j.get("errors") or []) if isinstance(e, str)]
        rec["warnings"] += [w if isinstance(w, str) else json.dumps(w, ensure_ascii=False)
                            for w in (j.get("warnings") or [])]
        rec["numErrors"] = j.get("totalNumErrors", j.get("numErrors"))
        rec["numWarnings"] = j.get("totalNumWarnings", j.get("numWarnings"))
        rec["numObjects"] = j.get("numObjects")
        if (j.get("totalNumErrors") or 0) > 0:
            rec["ok"] = False
    out.append(rec)
    print(json.dumps(rec, ensure_ascii=False)[:400], flush=True)
    time.sleep(5)

json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TOTAL pages=%d ok=%d errors=%d" % (len(out), sum(1 for r in out if r["ok"]),
                                          sum(len(r["errors"]) for r in out)))
print("FINAL_JSON_BEGIN")
print(json.dumps(out, ensure_ascii=False))
print("FINAL_JSON_END")
