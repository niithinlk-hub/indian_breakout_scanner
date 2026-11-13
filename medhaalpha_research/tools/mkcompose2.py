import base64, hashlib, sys, zlib, yaml
sp = sys.argv[1]
src = open(sp + "/tools/dryrun.py").read()
h = hashlib.sha256(src.encode()).hexdigest()
b64 = base64.b64encode(zlib.compress(src.encode(), 9)).decode()
lines = [b64[i:i + 76] for i in range(0, len(b64), 76)]
wrap = ("import base64,hashlib,sys,zlib; s=zlib.decompress(base64.b64decode(''.join(sys.argv[1].split()))).decode(); "
        "h=hashlib.sha256(s.encode()).hexdigest(); print('script sha256', h, flush=True); "
        "exec(compile(s, 'dryrun', 'exec')) if h == '%s' else print('HASH MISMATCH: script not run', flush=True)" % h)
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
    tmpfs:
      - /tmp:size=128m
    environment:
      ENGINE_URL: http://127.0.0.1:9
      SCANNER_TOKEN: ""
      DATABASE_URL: sqlite:////tmp/unused.db
      DRY_MODEL: fable_op
      PYTHONDONTWRITEBYTECODE: "1"
      HOME: /tmp
    volumes:
      - live_scanner_data:/data:ro
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
got = zlib.decompress(base64.b64decode("".join(arg.split()))).decode()
assert got == src and doc["services"]["dryrun"]["entrypoint"][2] == wrap and "$" not in out
open(sp + "/compose_dryrun2.yml", "w").write(out)
open(sp + "/argv_wrap2.txt", "w").write(wrap)
open(sp + "/argv_script2.txt", "w").write(arg)
print("script", len(src), "-> zlib+b64", len(b64), "chars in", len(lines), "lines | yaml", len(out), "chars | sha256", h)
