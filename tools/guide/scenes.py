import os
"""Run the guide's game scenes (scene.mjs), a few at a time.
    python scenes.py [name ...]"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "guide")  # work files and images (not committed)
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")

SCENES = {
    "truck": {"passes": 8, "shots": {"1": "truck_a", "4": "truck_b", "7": "truck_c"}},
    "ladder": {"keys": "right:20-62,down:63-120", "passes": 90, "shots": {"70": "ladder_a", "78": "ladder_b"}},
    "pipe": {"start": [27, 9, 21, 0, 0, 2, 0], "keys": "right:0-15", "passes": 30, "shots": {"10": "pipe_a", "18": "pipe_b", "22": "pipe_c"}},
    "slope": {"start": [21, 11, 18, 0, 0, 1, 0], "keys": "right:3-60", "passes": 40,
              "shots": {"10": "slope_a", "16": "slope_b", "22": "slope_c"}},
    "lift": {"start": [34, 2, 17, 0, 0, 0, 0], "power": True, "passes": 70,
             "shots": {"8": "lift_a", "30": "lift_b", "55": "lift_c"}},
    "train": {"start": [74, 12, 4, 0, 0, 3, 8], "power": True, "passes": 60, "shots": {"30": "train_a", "50": "train_b"}},
    "liftbar": {"start": [26, 4, 10, 0, 0, 1, 0], "power": True, "passes": 60, "shots": {"20": "bar_a", "45": "bar_b"}},
    "milk": {"start": [33, 8, 12, 0, 0, 1, 0], "carry": 8, "pokes": {"delivered": [0, 7, 0, 0]},
             "keys": "right:3-4,take:8-10", "passes": 40, "shots": {"6": "milk_a", "12": "milk_fall", "30": "milk_full"}},
    "lever": {"start": [115, 5, 12, 0, 0, 1, 0], "keys": "jump:5,right:5", "passes": 40,
              "shots": {"3": "lever_off", "9": "lever_jump", "30": "lever_on"}},
    "toy": {"start": [95, 5, 21, 0, 0, 1, 4], "carry": 0, "power": True, "pokes": {"delivered": [7, 0, 0, 0]},
            "keys": "left:3,take:8-10", "passes": 40, "shots": {"6": "toy_a", "13": "toy_fall", "30": "toy_made"}},
    "egg": {"start": [48, 14, 18, 0, 0, 1, 0], "factory": 0xE3, "carry": 0x27, "keys": "take:10-12", "passes": 40,
            "shots": {"8": "egg_before", "30": "egg_made"}},
    "deliver": {"start": [111, 19, 12, 0, 0, 1, 0], "carry": 0x28, "keys": "left:5-40", "passes": 45,
                "wait": 1, "shots": {"4": "deliver_a"}, "after": [[0.6, "deliver_truck"], [3, "deliver_b"]]},
    "dog": {"start": [2, 21, 28, 0, 0, 1, 0], "passes": 200, "shots": {"60": "dog_run", "195": "dog_sat"}},
    "dino": {"start": [120, 21, 3, 0, 0, 1, 0], "passes": 40, "shots": {"20": "dino"}},
    "drips": {"start": [94, 21, 9, 0, 0, 1, 0], "passes": 120, "shots": {"60": "drips_a", "100": "drips_b"}},
    "spider": {"start": [4, 21, 2, 0, 0, 1, 0], "passes": 40, "shots": {"30": "spider"}},
    "rm_33": {"start": [33, 8, 11, 0, 0, 1, 0], "passes": 10, "shots": {"8": "rm_33"}},
    "rm_51": {"start": [51, 10, 25, 0, 0, 1, 0], "passes": 10, "shots": {"8": "rm_51"}},
    "rm_110": {"start": [110, 7, 3, 0, 0, 1, 0], "passes": 10, "shots": {"8": "rm_110"}},
    "rm_95": {"start": [95, 5, 24, 0, 0, 1, 0], "passes": 10, "shots": {"8": "rm_95"}},
    "rm_115": {"start": [115, 5, 4, 0, 0, 1, 0], "passes": 10, "shots": {"8": "rm_115"}},
    "rm_48": {"start": [48, 14, 18, 0, 0, 1, 0], "passes": 10, "shots": {"8": "rm_48"}},
    "rm_111": {"start": [111, 19, 12, 0, 0, 1, 0], "passes": 10, "shots": {"8": "rm_111"}},
    "girder": {"start": [96, 11, 11, 0, 0, 1, 0], "keys": "take:10-12", "passes": 40, "shots": {"8": "girder_a", "30": "girder_b"}},
    "liftsign": {"start": [105, 11, 3, 0, 0, 1, 0], "keys": "jump:5,right:5", "passes": 40, "shots": {"3": "lift_sign", "30": "out_of_order"}},
    "basket": {"start": [24, 21, 22, 0, 0, 1, 0], "keys": "right:5-30,take:20-26", "passes": 40, "shots": {"35": "basket"}},
    "croc": {"start": [30, 21, 2, 0, 0, 1, 0], "passes": 60, "shots": {"30": "croc"}},
}


def run(name):
    spec = SCENES[name]
    r = subprocess.run(["node", f"{W}/work/scene.mjs", json.dumps(spec), f"{W}/work/scenes"],
                       cwd=REPO, capture_output=True, text=True, timeout=900)
    return name, r.stdout + r.stderr


names = sys.argv[1:] or list(SCENES)
with ThreadPoolExecutor(3) as ex:
    for name, out in ex.map(run, names):
        print(f"== {name}\n{out}", flush=True)
