"""Logs the state of all station connectors in a COPY of a save.

The save and the player's mods are copied into tests/.env-probe; the original save is
never opened or written. The probe mod logs every connector (BULKPROBE lines).

Usage: python tests/probe.py <save name or path> [path-to-factorio.exe]
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV = os.path.join(ROOT, "tests", ".env-probe")
DEFAULT_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\Factorio\bin\x64\factorio.exe"
USER = os.path.join(os.environ.get("APPDATA", ""), "Factorio")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    save = sys.argv[1]
    if not os.path.exists(save):
        save = os.path.join(USER, "saves", save if save.endswith(".zip") else save + ".zip")
    exe = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_EXE
    shutil.rmtree(ENV, ignore_errors=True)
    mods = os.path.join(ENV, "mods")
    shutil.copytree(os.path.join(USER, "mods"), mods)
    shutil.copytree(os.path.join(ROOT, "tests", "bulk-wagons-probe"), os.path.join(mods, "bulk-wagons-probe"))
    with open(os.path.join(mods, "mod-list.json")) as f:
        mod_list = json.load(f)
    mod_list["mods"] = [m for m in mod_list["mods"] if m["name"] != "bulk-wagons-probe"]
    mod_list["mods"].append({"name": "bulk-wagons-probe", "enabled": True})
    with open(os.path.join(mods, "mod-list.json"), "w") as f:
        json.dump(mod_list, f)
    copy = os.path.join(ENV, "probe.zip")
    shutil.copy(save, copy)
    write = os.path.join(ENV, "write")
    os.makedirs(os.path.join(ENV, "config"))
    with open(os.path.join(ENV, "config", "config.ini"), "w") as f:
        f.write("[path]\nread-data=__PATH__executable__/../../data\n")
        f.write("write-data=" + write.replace("\\", "/") + "\n")
    cmd = [exe, "--config", os.path.join(ENV, "config", "config.ini"), "--mod-directory", mods, "--disable-audio",
           "--benchmark", copy, "--benchmark-ticks", "2", "--benchmark-runs", "1"]
    env = dict(os.environ, SteamAppId="427520", SteamGameId="427520")
    run = subprocess.run(cmd, capture_output=True, text=True, errors="replace", env=env)
    log_path = os.path.join(write, "factorio-current.log")
    log = open(log_path, encoding="utf-8", errors="replace").read() if os.path.exists(log_path) else run.stdout
    lines = [l for l in log.splitlines() if "BULKPROBE" in l or "Error" in l]
    print("\n".join(lines) if lines else log[-4000:])


if __name__ == "__main__":
    main()
