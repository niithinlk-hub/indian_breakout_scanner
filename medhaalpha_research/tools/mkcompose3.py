import ast, base64, hashlib, sys, zlib, yaml
sp = sys.argv[1]
src = open(sp + "/tools/dryrun.py").read()
t = ast.parse(src)
for n in ast.walk(t):
    if isinstance(n, (ast.FunctionDef, ast.Module)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant) and isinstance(n.body[0].value.value, str):
        n.body = n.body[1:] or [ast.Pass()]
mini = "\n".join(" " * ((len(l) - len(l.lstrip(" "))) // 4) + l.lstrip(" ") for l in ast.unparse(t).split("\n")) + "\n"
compile(mini, "mini", "exec")
assert ast.dump(ast.parse(mini)) == ast.dump(t)          # same program as the tested source, minus docstrings
open(sp + "/tools/dryrun_min.py", "w").write(mini)
h = hashlib.sha256(mini.encode()).hexdigest()
b64 = base64.b64encode(zlib.compress(mini.encode(), 9)).decode()
W = 128
lines = [b64[i:i + W] for i in range(0, len(b64), W)]
wrap = ("import base64,hashlib,sys,zlib; s=zlib.decompress(base64.b64decode(''.join(sys.argv[1].split()))).decode(); "
        "h=hashlib.sha256(s.encode()).hexdigest(); print('script sha256', h, flush=True); "
        "exec(compile(s, 'dryrun', 'exec')) if h == '%s' else print('HASH MISMATCH: not run', flush=True)" % h)
head = '''services:
  dryrun:
    image: vitezza-scanner
    pull_policy: never
    read_only: true
    user: "65534:65534"
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    cpus: 0.3
    mem_limit: 512m
    pids_limit: 64
    restart: "no"
    tmpfs: ["/tmp:size=128m"]
    environment:
      ENGINE_URL: http://127.0.0.1:9
      SCANNER_TOKEN: ""
      DATABASE_URL: sqlite:////tmp/unused.db
      PYTHONDONTWRITEBYTECODE: "1"
      HOME: /tmp
    volumes: ["live_scanner_data:/data:ro"]
    entrypoint:
      - python
      - -c
      - "%s"
    command:
      - |
''' % wrap
tail = '''volumes:
  live_scanner_data:
    external: true
    name: vitezza_scanner_data
'''
out = head + "".join("        " + l + "\n" for l in lines) + tail
doc = yaml.safe_load(out)
arg = doc["services"]["dryrun"]["command"][0]
assert zlib.decompress(base64.b64decode("".join(arg.split()))).decode() == mini and doc["services"]["dryrun"]["entrypoint"][2] == wrap and "$" not in out
open(sp + "/compose_dryrun3.yml", "w").write(out)
open(sp + "/argv_wrap3.txt", "w").write(wrap)
open(sp + "/argv_script3.txt", "w").write(arg)
print("src", len(src), "mini", len(mini), "-> b64", len(b64), "in", len(lines), "lines | yaml", len(out), "chars (limit 8192) | sha256", h)
