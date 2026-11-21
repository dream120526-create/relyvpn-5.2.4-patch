# -*- coding: utf-8 -*-
import os, sys, zipfile, shutil, struct, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = r"F:\Agent_Work\Code\relyvpn-patch\work\stage"
APP = os.path.join(WORK, "Payload", "RelyVPN.app")

def cryptid(path):
    d = open(path, "rb").read()
    ncmds = struct.unpack("<I", d[16:20])[0]
    off = 32
    for _ in range(ncmds):
        cmd, size = struct.unpack("<II", d[off:off+8])
        if cmd in (0x2c, 0x2d):
            c_off, c_size, cid = struct.unpack("<III", d[off+8:off+20])
            return cid, c_size
        off += size
    return None, 0

targets = {
 "RelyVPN": os.path.join(APP, "RelyVPN"),
 "App.framework/App": os.path.join(APP, "Frameworks", "App.framework", "App"),
 "Flutter": os.path.join(APP, "Frameworks", "Flutter.framework", "Flutter"),
 "RelyVPNTunnel": os.path.join(APP, "PlugIns", "RelyVPNTunnel.appex", "RelyVPNTunnel"),
}
print("=== encryption info (cryptid 0 = decrypted) ===")
for k, p in targets.items():
    cid, csize = cryptid(p)
    print("  %-20s cryptid=%s cryptsize=%d" % (k, cid, csize))

# clean nested SC_Info + store metadata
removed = []
for root, dirs, files in os.walk(WORK):
    for d in list(dirs):
        if d == "SC_Info":
            shutil.rmtree(os.path.join(root, d))
            removed.append(os.path.relpath(os.path.join(root, d), WORK))
            dirs.remove(d)
for extra in ["META-INF", "iTunesMetadata.plist"]:
    p = os.path.join(WORK, extra)
    if os.path.isdir(p):
        shutil.rmtree(p); removed.append(extra)
    elif os.path.exists(p):
        os.remove(p); removed.append(extra)
print("cleaned:", len(removed), "items")

OUT = r"F:\Agent_Work\Code\relyvpn-patch\dist"
dst = os.path.join(OUT, "RelyVPN-5.2.4-devicerotate-unsigned.ipa")
if os.path.exists(dst): os.remove(dst)

def should_exec(path):
    return os.path.basename(path) in ("RelyVPN","RelyVPNTunnel","Flutter","App","objective_c","rely_transport","rely_speedtest")

count = 0
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, dirs, files in os.walk(WORK):
        for fn in files:
            full = os.path.join(root, fn)
            arc = os.path.relpath(full, WORK).replace("\\", "/")
            if not arc.startswith("Payload/"):
                continue
            zi = zipfile.ZipInfo(arc)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (0o100755 if should_exec(full) else 0o100644) << 16
            with open(full, "rb") as f:
                z.writestr(zi, f.read())
            count += 1

h = hashlib.sha256(open(dst,"rb").read()).hexdigest().upper()
print("files:", count, "size:", os.path.getsize(dst))
print("sha256:", h)

z2 = zipfile.ZipFile(dst)
print("verify testzip:", z2.testzip())
print("leftovers:", [n for n in z2.namelist() if "_CodeSignature" in n or "SC_Info" in n or not n.startswith("Payload/")])
