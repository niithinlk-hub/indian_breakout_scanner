import json,sys,base64,hashlib,io,tarfile,os
p,out=sys.argv[1],sys.argv[2]
d=json.load(open(p))
lines=[]
for svc in d:
    if svc["service"].startswith("inspect"):
        lines=[e["line"] for e in svc["entries"]]
i=lines.index("===B64"); j=lines.index("===END")
print("\n".join(lines[:i]))
raw=base64.b64decode("".join(lines[i+1:j]))
print("sha256 local:",hashlib.sha256(raw).hexdigest(), len(raw),"bytes")
tf=tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz")
for m in tf.getmembers():
    assert m.isfile() and not m.name.startswith("/") and ".." not in m.name, m.name
tf.extractall(out, filter="data")
print("extracted", len(tf.getnames()))
