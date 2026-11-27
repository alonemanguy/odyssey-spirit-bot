from pathlib import Path

def rewrite(path, pairs):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in s:
            raise SystemExit("missing pattern in %s: %r" % (path, old[:60]))
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")

rewrite("odyssey_data.py", [("`odysseyland.aternos.me`", "`odysseyland.aternos.me:56870`")])
rewrite("wake_once.py", [(
 '        return ("**Bringing the server up** - give it a minute, then java "\n'
 '                "`odysseyland.aternos.me` or bedrock `odysseyland.aternos.me` "\n'
 '                "port `19132`.")',
 '        return ("**Bringing the server up** - give it a minute, then Java "\n'
 '                "`odysseyland.aternos.me:56870` or Bedrock same host, port `19132`.")',
)])
rewrite("odyssey_bot.py", [('"SERVER_JAVA_PORT", "25565"', '"SERVER_JAVA_PORT", "56870"')])
