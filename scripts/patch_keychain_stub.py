# -*- coding: utf-8 -*-
import os, sys, glob, zipfile, shutil, struct, json, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"F:\Agent_Work\Code\relyvpn-patch\orig"
IPA = [p for p in glob.glob(os.path.join(SRC, "*.ipa")) if "VPN" in os.path.basename(p)][0]
WORK = r"F:\Agent_Work\Code\relyvpn-patch\work\stage"
if os.path.isdir(WORK):
    shutil.rmtree(WORK)
os.makedirs(WORK, exist_ok=True)

with zipfile.ZipFile(IPA) as z:
    z.extractall(WORK)
print("extracted")

appdir = None
for d in os.listdir(os.path.join(WORK, "Payload")):
    if d.endswith(".app"):
        appdir = os.path.join(WORK, "Payload", d)
print("app:", appdir)

exe = os.path.join(appdir, "RelyVPN")
b = bytearray(open(exe, "rb").read())
print("exe size", len(b))

# verify stub bytes at 0x6b278: adrp/ldr/br for _SecItemCopyMatching
off = 0x6b278
print("stub bytes:", b[off:off+12].hex())
print("ldr at 0x%x: %s" % (off+4, b[off+4:off+8].hex()))
assert b[off+4:off+8].hex() == "10aa40f9", "unexpected ldr encoding"

# patch ldr offset 0x150 -> 0x158 (SecItemDelete GOT slot)
b[off+5] = 0xAE
print("after patch:", b[off:off+12].hex())
assert b[off+4:off+8].hex() == "10ae40f9"

open(exe, "wb").write(bytes(b))

# strip signature dirs
removed = []
for rel in ["_CodeSignature", "SC_Info", "PlugIns"]:
    p = os.path.join(appdir, rel)
    if rel == "PlugIns":
        continue
    if os.path.isdir(p):
        shutil.rmtree(p); removed.append(rel)
for root, dirs, files in os.walk(appdir):
    for d in list(dirs):
        if d == "_CodeSignature":
            shutil.rmtree(os.path.join(root, d)); removed.append(os.path.join(os.path.relpath(root, appdir), d)); dirs.remove(d)
for f in ["embedded.mobileprovision"]:
    p = os.path.join(appdir, f)
    if os.path.exists(p):
        os.remove(p); removed.append(f)
print("removed:", removed)

# repack with correct permissions
OUT = r"F:\Agent_Work\Code\relyvpn-patch\dist"
os.makedirs(OUT, exist_ok=True)
dst = os.path.join(OUT, "RelyVPN-5.2.4-devicerotate-unsigned.ipa")
if os.path.exists(dst):
    os.remove(dst)

def should_exec(path):
    name = os.path.basename(path)
    if name in ("RelyVPN", "RelyVPNTunnel", "Flutter", "App", "objective_c", "rely_transport", "rely_speedtest"):
        return True
    ext = os.path.splitext(name)[1]
    return ext in (".dylib", ".so")

count = 0
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, dirs, files in os.walk(WORK):
        for fn in files:
            full = os.path.join(root, fn)
            arc = os.path.relpath(full, WORK).replace("\\", "/")
            zi = zipfile.ZipInfo(arc)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (0o100755 if should_exec(full) else 0o100644) << 16
            with open(full, "rb") as f:
                z.writestr(zi, f.read())
            count += 1

h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
print("packed files:", count)
print("out:", dst)
print("size:", os.path.getsize(dst))
print("sha256:", h)
