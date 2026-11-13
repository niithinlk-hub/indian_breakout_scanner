import ast, base64, hashlib, sys, zlib, yaml
sp, name = sys.argv[1], sys.argv[2]
src = open(sp + "/tools/%s.py" % name).read()
t = ast.parse(src)
mini = "\n".join(" " * ((len(l) - len(l.lstrip(" "))) // 4) + l.lstrip(" ") for l in ast.unparse(t).split("\n")) + "\n"
compile(mini, "mini", "exec")
assert ast.dump(ast.parse(mini)) == ast.dump(t)
h = hashlib.sha256(mini.encode()).hexdigest()
b64 = base64.b64encode(zlib.compress(mini.encode(), 9)).decode()
W = 128
lines = [b64[i:i + W] for i in range(0, len(b64), W)]
wrap = ("import base64,hashlib,sys,zlib; s=zlib.decompress(base64.b64decode(''.join(sys.argv[1].split()))).decode(); "
        "h=hashlib.sha256(s.encode()).hexdigest(); print('script sha256', h, flush=True); "
        "exec(compile(s, 'helper', 'exec')) if h == '%s' else print('HASH MISMATCH: not run', flush=True)" % h)
head = '''services:
  inspect:
    image: vitezza-scanner
    pull_policy: never
    read_only: true
    network_mode: none
    user: "65534:65534"
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    cpus: 0.3
    mem_limit: 512m
    pids_limit: 64
    restart: "no"
    tmpfs: ["/tmp:size=64m"]
    environment:
      ENGINE_URL: http://127.0.0.1:9
      SCANNER_TOKEN: ""
      DATABASE_URL: sqlite:////tmp/unused.db
      PYTHONDONTWRITEBYTECODE: "1"
      HOME: /tmp
    entrypoint:
      - python
      - -c
      - "%s"
    command:
      - |
''' % wrap
out = head + "".join("        " + l + "\n" for l in lines)
doc = yaml.safe_load(out)
arg = doc["services"]["inspect"]["command"][0]
assert zlib.decompress(base64.b64decode("".join(arg.split()))).decode() == mini and doc["services"]["inspect"]["entrypoint"][2] == wrap and "$" not in out
open(sp + "/compose_%s.yml" % name, "w").write(out)
print("src", len(src), "mini", len(mini), "yaml", len(out), "chars (limit 8192) | sha256", h)
