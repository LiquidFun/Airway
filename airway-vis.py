#!/usr/bin/env python3

import os 
import sys
import argparse
import subprocess


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("id", default="1", help="patient id (can be index, name, or id)")
    parser.add_argument("-p", "--path", default=f"/default/path", help="working path")
    parser.add_argument("-s", "--splits", default=False, action="store_true", help="show plot of splits")
    parser.add_argument("-b", "--bronchus", default=False, action="store_true", help="show plot of bronchus")
    parser.add_argument("-l", "--lobes", default=False, action="store_true", help="show plot of lobes")
    args = parser.parse_args()

    patient = args.id
    if patient.capitalize() in KEYS:
        patient = KEYS[patient.capitalize()]
    variants = [key for key, val in KEYS.items() if val == patient] + [patient]
    print(f"Showing patient with id {', '.join(variants)}")
    source_path = os.path.join(args.path, f"stage-04/{patient}")
    target_path = os.path.join(args.path, f"stage-22/{patient}")

    scripts_to_run = []
    if args.bronchus:
        scripts_to_run.append(("visualization/plot_splits.py", ["True", "True"]))
    elif args.lobes:
        scripts_to_run.append(("visualization/plot_lobes.py", ["True", "True"]))
    else:
        scripts_to_run.append(("visualization/plot_splits.py", ["True", "False"]))

    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    for script, script_args in scripts_to_run:
        ret_val = subprocess.run([
                'python3',
                os.path.join(base_path, script),
                source_path,
                target_path,
                *script_args,
            ],
            capture_output=True,
            encoding='utf-8'
        )
        print("STDOUT:\n{}\n\nSTDERR:\n{}\n\n".format(ret_val.stdout, ret_val.stderr))

# Don't look at this! Your eyes may fall out! TODO: Maybe perhaps redo this
KEYS = {"1": "3127679", "Buha": "3127679", "2": "3128219", "Dudo": "3128219", "3": "3128221", "Tene": "3128221", "4": "3128357", "Yaru": "3128357", "5": "3128363", "Coki": "3128363", "6": "3128458", "Xute": "3128458", "7": "3129087", "Puhu": "3129087", "8": "3131734", "Joye": "3131734", "9": "3132481", "Nero": "3132481", "10": "3133592", "Salu": "3133592", "11": "3133629", "Lake": "3133629", "12": "3134186", "Kamu": "3134186", "13": "3137792", "Laje": "3137792", "14": "3138933", "Mewi": "3138933", "15": "3139289", "Reto": "3139289", "16": "3139674", "Haki": "3139674", "17": "3142930", "Tiya": "3142930", "18": "3143391", "Zino": "3143391", "19": "3143510", "Paji": "3143510", "20": "3143713", "Sezu": "3143713", "21": "3159505", "Rado": "3159505", "22": "3159529", "Juti": "3159529", "23": "3159550", "Vimo": "3159550", "24": "3159855", "Wabi": "3159855", "25": "3159939", "Hapo": "3159939", "26": "3160096", "Tama": "3160096", "27": "3160394", "Yogu": "3160394", "28": "3161660", "Zeso": "3161660", "29": "3161827", "Leyi": "3161827", "30": "3162022", "Yodi": "3162022", "31": "3163230", "Jiwo": "3163230", "32": "3163971", "Mati": "3163971", "33": "3163974", "Suda": "3163974", "34": "3165694", "Name": "3165694", "35": "3166082", "Fale": "3166082", "36": "3166127", "Wazo": "3166127", "37": "3176932", "Noti": "3176932", "38": "3177265", "Paji": "3177265", "39": "3179231", "Yeli": "3179231", "40": "3179381", "Fove": "3179381", "41": "3180063", "Hayo": "3180063", "42": "3180073", "Mope": "3180073", "43": "3180185", "Hiza": "3180185", "44": "3180368", "Konu": "3180368", "45": "3180687", "Hoyo": "3180687", "46": "3180695", "Cexo": "3180695", "47": "3182057", "Gulo": "3182057", "48": "3182100", "Payi": "3182100", "49": "3182731", "Tute": "3182731", "50": "3183090", "Lahi": "3183090", "51": "3184754", "Teya": "3184754", "52": "3185469", "Kuzu": "3185469", "53": "3185729", "Gevo": "3185729", "54": "3185881", "Fafi": "3185881", "55": "3185963", "Cefe": "3185963", "56": "3186205", "Nowo": "3186205", "57": "3186634", "Qehu": "3186634", "58": "3188855", "Dazi": "3188855", "59": "3189891", "Lisa": "3189891", "60": "3190143", "Qevo": "3190143", "61": "3190321", "Gegi": "3190321", "62": "3190525", "Kadi": "3190525", "63": "3190583", "Cizu": "3190583", "64": "3191006", "Futa": "3191006", "65": "3191253", "Yedu": "3191253", "66": "3191282", "Gapu": "3191282", "67": "3191910", "Nucu": "3191910", "68": "3191978", "Beho": "3191978", "69": "3191993", "Giqa": "3191993", "70": "3192387", "Kifu": "3192387", "71": "3193003", "Negi": "3193003", "72": "3193919", "Zaxo": "3193919", "73": "3194121", "Zupo": "3194121", "74": "3228498", "Niso": "3228498", "75": "3229571", "Jita": "3229571", "76": "3254404", "Loxu": "3254404", "77": "3480207", "Rezo": "3480207"}

if __name__ == "__main__":
    run()

