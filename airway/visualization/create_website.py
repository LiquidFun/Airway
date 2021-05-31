#!/usr/bin/env python3
""" Stage 29 - Website generation

prerequisites:
    stage 7  (*.graphml)
    stage 10 (classification.csv)
    stage 11 (metadata)
    stage 21 (object files)
    stage 22 (tree evolution) (default precondition)
    stage 23 (2d plots) 

"""
import sys
import os
import shutil
import platform
import subprocess
from pathlib import Path
from hashlib import sha256

import pandas as pd

base_path = str(Path(sys.argv[0]).parents[0])


def load_template(template_path=base_path + "/website/template.html"):
    """
    load the html template file from airway repository and returns it
    """

    with open(
        template_path,
        "r",
    ) as template_file:
        return template_file.read()


def build_header(template):
    """
    replace the corresponding variable in the template file with the header and
    returns the altered template
    """
    header = '<h1><a href="../index.html">Airway - Database</a></h1>'
    return template.replace("%header", header)


def build_pat_menu(template):
    """
    replace cooresponding variable in the template file with the navigation bar
    """

    # links are build from patients dirs from previous stage
    pat_list = os.listdir(path=str(source_path.parents[0]))
    l = ""
    for pat in sorted(pat_list):
        meta_row = metadata[metadata["PatientID"] == int(pat)].squeeze()
        l += "\n<li><a href=../{}/{}.html><b>{:0=3}</b>..{}({})</a></li>\n".format(
            pat, pat, meta_row["#"], pat, meta_row["Name"]
        )
    return template.replace("%patMenu", l)


def build_description(template):
    """
    replace the corresponding variable in the template file with the description
    of the patient and returns the altered template
    """

    meta_row = metadata[metadata["PatientID"] == int(pat_id)].squeeze()
    date = str(meta_row["AcquisitionDate"])
    if len(date) == 8:  # convert to ISO8601 - YYYY-MM-DD
        date = "{}-{}-{}".format(date[0:4], date[4:6], date[6:8])

    machine = str(meta_row["Manufacturer"]) + " "
    machine += str(meta_row["ManufacturerModelName"])

    class_row = classification[classification["patient"] == int(pat_id)].squeeze()

    descr = "<table>\n"
    descr += "<tr><th>NAME:</th><td>{}</td></tr>\n".format(meta_row["Name"])
    descr += "<tr><th>ID:</th><td>{}</td></tr>\n".format(meta_row["PatientID"])
    descr += "<tr><th>SEX:</th><td>{}</td></tr>\n".format(meta_row["PatientSex"])
    descr += "<tr><th>DATE:</th><td>{}</td></tr>\n".format(date)
    descr += "<tr><th>MACHINE:</th><td>{}</td></tr>\n".format(machine)
    descr += "<tr><th>SLICE-THICKNESS:</th><td>{} mm</td></tr>\n".format(meta_row["SliceThickness"])
    descr += "<tr><th>HISTORY:</th><td>{}</td></tr>\n".format(meta_row["AdditionalPatientHistory"])
    descr += "<tr><th>CLASSIFICATION:</th><td>{}</td></tr>\n".format(class_row["classification"])
    descr += "</table>"

    return template.replace("%patDescription", descr)


def copy_files(source_path, target_path, glob="*.svg"):
    """
    copy the files matching a given pattern from source_path to target_path.

    source_path and target_path needs to be Path like objects.

    only changed files will be copied, therefore a sha256 digest is calculated on
    source and destination files

    Return file list from source_path
    """

    files = list(source_path.glob(glob))
    # copy all files to stage-23 if digest differs (files have been changed)
    target_list = []
    for src in files:
        target = target_path.joinpath(src.name)
        if not target.exists():
            shutil.copy(str(src), str(target))
        else:
            src_digest = sha256(src.read_bytes()).hexdigest()
            target_digest = sha256(target.read_bytes()).hexdigest()
            if src_digest != target_digest:
                shutil.copy(str(src), str(target))
    return files


def build_pictures(template):
    """
    replace corresponding variable in template file with all pics from prev stage
    """

    pics = sorted(copy_files(plot_path, target_path, glob="*.png"), reverse=True)
    pic_names = [
        ("lobe-2", "left lower lobe<br>(Bronchus lobaris inferior sinister)"),
        ("lobe-3", "left upper lobe<br>(Bronchus lobaris superior sinister)"),
        ("lobe-4", "right lower lobe<br>(Bronchus lobaris inferior dexter)"),
        ("lobe-5", "right middle lobe<br>(Bronchus lobaris medius)"),
        ("lobe-6", "right upper lobe<br>(Bronchus lobaris superior dexter)"),
        ("tree", "complete split tree"),
    ]
    pic_names.reverse()
    l = ""
    name_counter = 0
    for pic in pics:
        if name_counter < 6:
            for key, val in pic_names:
                if pic.name.startswith(key):
                    descr = val
        else:
            descr = ""
        n = "\n<br><b>{}</b><br><br>\n".format(descr)
        if pic.name.startswith("tree"):
            s = '<img id=\'imgBig\' src="{}" alt="{}">'.format(pic.name, descr)
        else:
            s = '<img src="{}" alt="{}">'.format(pic.name, descr)
        l += n + '\n<br><a href="{}">{}</a><br><br><br>\n'.format(pic.name, s)
        name_counter += 1
    if len(pics) == 0:
        l = "\n<b>No pictures available</b>\n"
    return template.replace("%patPictures", l)


def build_evolution_of_tree(template):
    """
    replace corresponding variable in template file with all pics from prev stage
    """

    pics = copy_files(source_path, target_path, glob="*.png")
    l = ""
    for pic in pics:
        s = '<img id=\'imgBig\' src="{}" alt="{}">'.format(pic.name, pic.name)
        l += '\n<br><a href="{}">{}</a><br>\n'.format(pic.name, s)
    if len(pics) == 0:
        l = "\n<b>No pictures available.</b>\n"
    return template.replace("%treeEvolution", l)


def build_links(current_template):
    """
    link generation, takes the template, returns the altered template
    """

    fs_link = '<br><a href="fullscreen-bronchus.html" target="_blank">view bronchus in fullscreen</a>'
    current_template = current_template.replace("%fullBronchusLink", fs_link)

    obj_archive, obj_size = create_object_archive(str(target_path) + "/" + pat_id + "-objects", obj_path)
    graph_archive, graph_size = create_object_archive(str(target_path) + "/" + pat_id + "-graphml-trees", tree_path)

    obj_link = '<a href="{}">download 3D-object files (zip {} MiB)</a>'.format(
        Path(obj_archive).name, round(obj_size / 1024 / 1024, 2)
    )

    graph_link = '<a href="{}">download all trees (zipped graphml {} KiB)</a>'.format(
        Path(graph_archive).name, round(graph_size / 1024, 1)
    )

    current_template = current_template.replace("%objectDownload", obj_link)
    current_template = current_template.replace("%graphDownload", graph_link)

    return current_template


def build_footer(current_template):
    """
    Writes footer to template
    """
    f = "<table>\n"
    f += "<tr><td>Systembiologie</td></tr>\n"
    f += "<tr><td>Institut für Informatik - Universität Rostock</td></tr>\n"
    f += "</table>\n"
    return current_template.replace("%footer", f)


def save_website(website, website_path):
    """
    write the final website to disk, should be the last step
    """

    with open(website_path, "w") as website_file:
        website_file.write(website)


def copy_style(dst_file, style_file=base_path + "/website/style.css"):
    """
    copy the style file from repo to target, if size differs
    """

    if not Path(dst_file).exists():
        shutil.copy(style_file, dst_file)
    elif Path(style_file).stat().st_size != Path(dst_file).stat().st_size:
        shutil.copy(style_file, dst_file)


def create_object_archive(object_download_name, obj_path):
    """
    creates a zipped file with the name given by object_download_name. All files
    in obj_path will be archived (obj_path itself) ist not part of the archive.
    """

    name = shutil.make_archive(object_download_name, "zip", obj_path)
    size = Path(name).stat().st_size
    return name, size


def simplify_object_files():
    """
    Using the external tool obj-simplify to erase redundancies from obj-model files.
    It is a precompiled binary for Linux, therefore it only works on Linux based systems.

    With the use of obj-simplify the obj-files will be 20+% less in space consumption.
    """

    objs_path = str(base_path) + "/website/bin/obj-simplify"

    if platform.machine() == "x86_64" and platform.system() == "Linux":
        obj_files = list(obj_path.glob("*on*.obj"))
        for obj in obj_files:
            arguments = [
                str(objs_path),
                "-no-duplicates",
                "-in",
                str(obj),
                "-out",
                str(target_path) + "/" + str(obj.name),
                "-quiet",
                "-no-progress",
                "-workers",
                "4",
            ]
            try:
                ret_val = subprocess.run(arguments, check=True, capture_output=True, encoding="utf-8")
                print(ret_val.stdout)
                sys.stderr.write(ret_val.stderr)
            except subprocess.CalledProcessError:
                print("\nobj-simplify could not be executed, copying files instead\n")
                copy_files(obj_path, target_path, glob="*on*.obj")
    else:
        print("\nNon Linux or not a 64 bit machine, just copying obj files\n")
        copy_files(obj_path, target_path, glob="*on*.obj")


def copy_js(dst_dir, js_dir=base_path + "/website/js/"):
    """
    copy the javascript files from repo to target, if their size differs
    """

    js_files = list(Path(js_dir).glob("*js"))
    target_dir = Path(dst_dir)
    if not target_dir.is_dir():
        try:
            target_dir.mkdir()
        except:
            print("{} already created by another process".format(target_dir))

    for j in js_files:
        target = target_dir.joinpath(j.name)
        if not target.exists():
            shutil.copy(j, target)
        elif j.stat().st_size != target.stat().st_size:
            shutil.copy(j, target)


if __name__ == "__main__":
    source_path = Path(sys.argv[1])
    target_path = Path(sys.argv[2])
    pat_id = source_path.parts[-1]

    # stage 7 (graphml-trees) needed
    tree_path = source_path.parents[1].joinpath("stage-07/" + pat_id)

    if not tree_path.is_dir():
        sys.stderr.write("ERROR: stage-07 needed")
        sys.stderr.write(str(tree_path))
        sys.exit(-1)

    # stage 10 (classification) needed
    classification_path = source_path.parents[1] / "stage-10" / "classification.csv"

    # stage 11 (metadata) needed
    metadata_path = source_path.parents[1] / "stage-11" / "metadata.csv"

    if not classification_path.exists():
        sys.stderr.write("ERROR: stage-10 needed")
        sys.stderr.write(str(metadata_path))
        sys.exit(-1)
    else:
        classification = pd.read_csv(str(classification_path))

    if not metadata_path.exists():
        sys.stderr.write("ERROR: stage-11 needed")
        sys.stderr.write(str(metadata_path))
        sys.exit(-1)
    else:
        metadata = pd.read_csv(str(metadata_path))

    # stage 21 (obj) needed
    obj_path = source_path.parents[1] / "stage-21" / pat_id

    if not obj_path.exists():
        sys.stderr.write("ERROR: stage-21 needed")
        sys.stderr.write(str(obj_path))
        sys.exit(-1)

    # stage 23 (2d plots) needed
    plot_path = source_path.parents[1] / "stage-23" / pat_id

    if not plot_path.exists():
        sys.stderr.write("ERROR: stage-23 needed")
        sys.stderr.write(str(obj_path))
        sys.exit(-1)

    # build website
    print("Building website for Patient {}".format(pat_id))
    copy_style(str(target_path.parents[0]) + "/style.css")
    copy_js(str(target_path.parents[0]) + "/js/")
    template = load_template()
    template = build_header(template)
    template = build_pat_menu(template)
    template = build_pictures(template)
    template = build_evolution_of_tree(template)
    template = build_description(template)
    template = build_links(template)
    template = build_footer(template)
    simplify_object_files()
    copy_files(Path(base_path + "/website/"), target_path, glob="fullscreen-*.html")
    copy_files(Path(base_path + "/website/"), target_path.parents[0], glob="index*.html")
    copy_files(Path(base_path + "/website/"), target_path.parents[0], glob="*.png")
    save_website(template, str(target_path) + "/" + pat_id + ".html")
