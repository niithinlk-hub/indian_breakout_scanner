import hashlib, sys, yaml
sp = sys.argv[1]
src = open(sp + "/tools/dryrun.py").read()
assert "$" not in src and "\t" not in src
body = "".join(("        " + l if l.strip() else "") + "\n" for l in src.rstrip("\n").split("\n"))
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
      - "import hashlib,sys; s=sys.argv[1]; h=hashlib.sha256(s.encode()).hexdigest(); print('script sha256', h, flush=True); exec(compile(s, 'dryrun', 'exec')) if h == 'EXPECTED' else print('HASH MISMATCH: script not run', flush=True)"
    command:
      - |
'''
tail = '''volumes:
  live_scanner_data:
    external: true
    name: vitezza_scanner_data
'''
doc = yaml.safe_load(head + body + tail)
script = doc["services"]["dryrun"]["command"][0]
h = hashlib.sha256(script.encode()).hexdigest()
out = (head + body + tail).replace("EXPECTED", h)
doc = yaml.safe_load(out)
assert doc["services"]["dryrun"]["command"][0] == script and h in doc["services"]["dryrun"]["entrypoint"][2]
open(sp + "/compose_dryrun.yml", "w").write(out)
open(sp + "/argv_wrap.txt", "w").write(doc["services"]["dryrun"]["entrypoint"][2])
open(sp + "/argv_script.txt", "w").write(script)
print("sha256", h, "| yaml bytes", len(out), "| script lines", script.count("\n"), "| same as file:", script == src)
print({k: v for k, v in doc["services"]["dryrun"].items() if k not in ("command", "entrypoint")}, doc["volumes"])
