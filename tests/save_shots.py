"""Takes screenshots of the bunkers and silos in a COPY of a save (opens a Factorio window briefly).

The save and the player's mods are copied into tests/.env-saveshots; the original save is
never opened or written. The harness mod finds the stations and photographs an overview of
each group and a close-up of each station with a wagon under it.

With --repo the mod from this repository replaces the player's bulk-wagons.

Usage: python tests/save_shots.py [--repo] <save name or path> [out_dir]   (default out_dir: previews/saveshots)
"""
import glob
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV = os.path.join(ROOT, "tests", ".env-saveshots")
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\Factorio\bin\x64\factorio.exe"
USER = os.path.join(os.environ.get("APPDATA", ""), "Factorio")
HARNESS = "bulk-wagons-saveshots"


def main():
    args = sys.argv[1:]
    repo = "--repo" in args
    args = [a for a in args if a != "--repo"]
    if not args:
        sys.exit(__doc__)
    save = args[0]
    if not os.path.exists(save):
        save = os.path.join(USER, "saves", save if save.endswith(".zip") else save + ".zip")
    out = args[1] if len(args) > 1 else os.path.join(ROOT, "previews", "saveshots")
    shutil.rmtree(ENV, ignore_errors=True)
    mods = os.path.join(ENV, "mods")
    shutil.copytree(os.path.join(USER, "mods"), mods)
    if repo:
        sys.path.insert(0, os.path.join(ROOT, "tests"))
        from run import MOD_FILES, MOD_DIRS
        for old in glob.glob(os.path.join(mods, "bulk-wagons_*.zip")):
            os.remove(old)
        target = os.path.join(mods, "bulk-wagons")
        shutil.rmtree(target, ignore_errors=True)
        os.makedirs(target)
        for f in MOD_FILES:
            if os.path.exists(os.path.join(ROOT, f)):
                shutil.copy(os.path.join(ROOT, f), target)
        for d in MOD_DIRS:
            shutil.copytree(os.path.join(ROOT, d), os.path.join(target, d))
    shutil.copytree(os.path.join(ROOT, "tests", HARNESS), os.path.join(mods, HARNESS))
    with open(os.path.join(mods, "mod-list.json")) as f:
        mod_list = json.load(f)
    mod_list["mods"] = [m for m in mod_list["mods"] if m["name"] != HARNESS]
    mod_list["mods"].append({"name": HARNESS, "enabled": True})
    with open(os.path.join(mods, "mod-list.json"), "w") as f:
        json.dump(mod_list, f)
    copy = os.path.join(ENV, "saveshots.zip")
    shutil.copy(save, copy)
    write = os.path.join(ENV, "write")
    os.makedirs(os.path.join(ENV, "config"))
    with open(os.path.join(ENV, "config", "config.ini"), "w") as f:
        f.write("[path]\nread-data=__PATH__executable__/../../data\n")
        f.write("write-data=" + write.replace("\\", "/") + "\n")
    cmd = [EXE, "--config", os.path.join(ENV, "config", "config.ini"), "--mod-directory", mods, "--disable-audio",
           "--benchmark-graphics", copy, "--benchmark-ticks", "60"]
    # Without these, the Steam build restarts itself through Steam when graphics are on.
    env = dict(os.environ, SteamAppId="427520", SteamGameId="427520")
    run = subprocess.run(cmd, capture_output=True, text=True, errors="replace", env=env)
    log_path = os.path.join(write, "factorio-current.log")
    log = open(log_path, encoding="utf-8", errors="replace").read() if os.path.exists(log_path) else run.stdout
    lines = [l for l in log.splitlines() if "BULKSHOTS" in l or "Error" in l]
    print("\n".join(lines) if lines else log[-4000:])
    shots = os.path.join(write, "script-output", "bulk-saveshots")
    if not os.path.isdir(shots):
        sys.exit("no screenshots taken")
    os.makedirs(out, exist_ok=True)
    for name in sorted(os.listdir(shots)):
        shutil.copy(os.path.join(shots, name), out)
        print(os.path.join(out, name))


if __name__ == "__main__":
    main()
