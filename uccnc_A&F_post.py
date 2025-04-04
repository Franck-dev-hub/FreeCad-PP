# -*- coding: utf-8 -*-

# See: https://wiki.freecad.org/Path_Post
#      https://wiki.freecad.org/Path_Postprocessor_Customization


import FreeCAD
from FreeCAD import Units
import Path
import PathScripts.PathUtils as PathUtils
import argparse
import datetime

# import shlex
import Path.Post.Utils as PostUtils
from builtins import open as pyopen

VERSION = "1.3"

TOOLTIP = """ Post processeur de notre machine.

import UCCNC_post
UCCNC_post.export(object,"/path/to/file.ncc","")
"""

# PREAMBLE_ possible values:
#    Multi line text with gcode. Preamble gcode
#    The preamble text will appear at the beginning of the GCODE output file.
PREAMBLE_DEFAULT = """
(Debut en-tete)
G17 (Sélection du plan XY)
G40 (Annulation de la compensation de rayon d'outil)
G49 (Désactivation de la compensation de longueur d'outil)
G54 (Activation de l'offset de travail G54)
G80 (Annulation des cycles)
G90 (Mode de positionnement absolu)
G94 (Mode d'avance en mm/min)
G53 Z-1 (Retour origine machgine en Z)
(Fin en-tete)

"""

PREAMBLE_DEFAULT_NO_COMMENT = """
(Debut en-tete)
G17 G49 G94
G40 G80 G90
G53 Z-1
(Fin en-tete)

"""


# POSTAMBLE possible values:
#    Multi line text with gcode. Postable gcode
#    The postamble text will appear following the last operation.
POSTAMBLE_DEFAULT = """
(Fin du programme)
M05 (Arrêt de la rotation de broche)
G40 (Annulation de la compensation de rayon d'outil)
G80 (Annulation des cycles)
G53 Z-1 (Retour au Z d'origine)
G53 Y200 (Retour au Y d'origine)
M30 (Arret du programme et retour au début)
(Programme fini)
"""

POSTAMBLE_DEFAULT_NO_COMMENT = """
(Fin de programme)
G40 G80
M05
G53 Z-1
G53 Y200
M30
(Programme fini)
"""

# PRE_OPERATION: Pre operation text will be inserted before every operation
PRE_OPERATION = """"""

# POST_OPERATION: Post operation text will be inserted after every operation
POST_OPERATION = """"""

# TOOL_CHANGE: Tool Change commands will be inserted before a tool change
TOOL_CHANGE = """"""

################################
# Other configuration settings #
################################

# SHOW_EDITOR possible values:
#    bool       Show gcode before saving.
#    True        before the file is written it is shown to the user for inspection
#    False       the file is written directly
#                set with --no-show-editor
if FreeCAD.GuiUp:
    SHOW_EDITOR = True
else:
    SHOW_EDITOR = False

# PROG_NAME possible values:
#   text    Name of the G-Code program
#                set with --name
PROG_NAME = "Programme"

# OUTPUT_HEADER possible values:
#   bool       Use of a document header
#    True        Use a predefined header.
#    False       Do not use a predefined header.
#                set with --no-header
OUTPUT_HEADER = True

# OUTPUT_COMMENTS possible values:
#    bool      (Dont) use comments in output
#    True        Use comments in output.
#    False       Suppress comments in output.
#                set with --no-comment
OUTPUT_COMMENTS = False

# OUTPUT_LINE_NUMBERS possible values:
#    bool      (Dont) use line numbers in output
#    True        Add a line number to each output line.
#    False       Do not add a line number.
#                set with --line-numbers
# note: line numbers Nxxxx are not supported by UC-CNC and are silently ignored.
OUTPUT_LINE_NUMBERS = True

# LINE_NUMBER_START possible values:
#    int    unsigned integer. Line number starting value
#    0..N
LINE_NUMBER_START = 0

# LINE_NUMBER_STEP possible values:
#    int    unsigned integer. Line number increment value
#    1..N
LINE_NUMBER_STEP = 1

# PREAMBLE possible values:
#    Multi line text with gcode. Preamble gcode
#    The preamble text will appear at the beginning of the GCODE output file.
#    set with --preamble
PREAMBLE = PREAMBLE_DEFAULT

# POSTAMBLE possible values:
#    Multi line text with gcode. Postable gcode
#    The postamble text will appear following the last operation.
#    set with --postable
POSTAMBLE = POSTAMBLE_DEFAULT

# MODAL possible values:
#   bool       Repeat/suppress repeated command arguments.
#    True        commands are suppressed if the same as previous line.
#    False       commands are repeated if the same as previous line.
#                set with --modal
MODAL = True

# REPEAT_ARGUMENTS possible values:
#   bool       Duplicate/suppressed axis values from the previous line.
#    True        All arguments are repreated in each command.
#    False       Equal values for arguments from the previous command are not repeated.
#                set with --repeat
REPEAT_ARGUMENTS = False

# USE_TLO possible values:
#   bool        Set tool length offset.
#    True        G43 will be output following tool changes.
#    False       No G43 used.
#                set with --tool-length-offset
USE_TLO = False

# TOOL_CHANGEMENT possible values:
#   bool        Set tool changement on/off.
#    True        Enable tool changement (M6).
#    False       Disable tool changement.
#                set with --tool-changement
TOOL_CHANGEMENT = False

# PRECISION possible values:
#   int         Number of digits in axis positions
#     0...N
#                set with --precision N
PRECISION = 3

# UNITS possible values:
#   GCODE       Code to switch to specific units
#     G20        US imperial [inch]
#     G21        Metric [mm]
#                set with --inches
# note: G20/G21 are not supported by UC-CNC, units are configured in a program profile.
#       In code G20/G21 commands are silently ignored by UC-CNC
#       UNITS is included in the post processor to mirror the profile settings.
UNITS_US_IMP = "G20"
UNITS_METRIC = "G21"
UNITS = UNITS_METRIC

# UNIT_FORMAT possible values: (see UNITS)
#   text        Text with specific units
#     "inch"     US imperial [inch]
#     "mm"       Metric [mm]
# note: G20/G21 are not supported by UC-CNC, units are configured in a program profile.
#       In code G20/G21 commands are silently ignored by UC-CNC
#       UNITS is included in the post processor to mirror the profile settings.
UNIT_FORMAT_US_IMP = "in"
UNIT_FORMAT_METRIC = "mm"
UNIT_FORMAT = UNIT_FORMAT_METRIC

# UNIT_SPEED_FORMAT possible values: (see UNITS)
#   text         Text with specific units over time units
#     "inch/min"  US imperial [inch]
#     "mm/min"    Metric [mm]
# note: G20/G21 are not supported by UC-CNC, units are configured in a program profile.
#       In code G20/G21 commands are silently ignored by UC-CNC
#       UNITS is included in the post processor to mirror the profile settings.
UNIT_SPEED_FORMAT_US_IMP = "in/min"
UNIT_SPEED_FORMAT_METRIC = "mm/min"
UNIT_SPEED_FORMAT = UNIT_SPEED_FORMAT_METRIC

##################################################
# No more configuration settings after this line #
##################################################

# see: https://docs.python.org/3/library/argparse.html
parser = argparse.ArgumentParser(prog=__name__, add_help=False)
parser.add_argument("--name", help="GCode program name")
parser.add_argument("--no-header", action="store_true", help="suppress header output")
parser.add_argument("--no-comments", action="store_true", help="suppress comment output")
parser.add_argument("--line-numbers", action="store_true", help="suppress prefix with line numbers")
parser.add_argument(
    "--no-show-editor",
    action="store_true",
    help="don't pop up editor before writing output",
)
parser.add_argument("--precision", default="3", help="number of digits of precision, default=3")
parser.add_argument(
    "--preamble",
    help='set commands to be issued before the first command, default="G17\nG90\nG54"',
)
parser.add_argument(
    "--postamble",
    help='set commands to be issued after the last command, default="M05\nM30"',
)
parser.add_argument("--inches", action="store_true", help="lengths in [in], G20")
parser.add_argument("--metric", action="store_true", help="lengths in [mm], G21")
parser.add_argument(
    "--modal", action="store_true", help="repeat/suppress repeated command arguments"
)
parser.add_argument(
    "--tool-length-offset",
    action="store_true",
    help="suppress tool length offset G43 following tool changes",
)
parser.add_argument(
    "--tool-changement",
    action="store_true",
    help="Enable / disable M6 for tool changement")
parser.add_argument("--repeat", action="store_true", help="repeat axis arguments")
TOOLTIP_ARGS = parser.format_help()


# debug option, trace to screen while processing to see where things break up.
trace_gcode = False

now = datetime.datetime.now()

LINENR = 0
COMMAND_SPACE = " "
UNIT_DEFAULT_CHANGED = False

# counting warnings and problems.
# Each warning/problem will appear as a WARNING:/PROBLEM: comment in the GCode output.
warnings_count = 0
problems_count = 0

HEADER = """(Post Processor version {})
({})
"""


def processArguments(argstring):
    global SHOW_EDITOR  # Show gcode before saving.
    global PROG_NAME  # Name of the G-Code program
    global OUTPUT_HEADER  # Use of a document header
    global OUTPUT_COMMENTS  # (Dont) use comments in output
    global OUTPUT_LINE_NUMBERS  # (Dont) use line numbers in output
    global PREAMBLE  # Preamble gcode
    global POSTAMBLE  # Postable gcode
    global MODAL  # Repeat/suppress repeated command arguments.
    global USE_TLO  # Set tool length offset
    global PRECISION  # Number of digits in feed and axis values
    global UNITS  # Code to switch to specific units
    global UNIT_FORMAT  # Text with specific units
    global UNIT_SPEED_FORMAT  # Text with specific units over time units
    global UNIT_DEFAULT_CHANGED  # tracing changes in UNIT settings.
    global REPEAT_ARGUMENTS  # Repeat or suppress axis values if the same as previous line.

    try:
        UNIT_DEFAULT_CHANGED = False
        args = parser.parse_args(argstring.split())

        if args.name is not None:
            PROG_NAME = args.name

        if args.no_header:
            OUTPUT_HEADER = False

        if args.no_comments:
            OUTPUT_COMMENTS = False

        if args.line_numbers:
            OUTPUT_LINE_NUMBERS = True

        if args.no_show_editor:
            SHOW_EDITOR = False

        PRECISION = args.precision

        if args.preamble is not None:
            PREAMBLE = args.preamble
        elif OUTPUT_COMMENTS:
            PREAMBLE = PREAMBLE_DEFAULT
        else:
            PREAMBLE = PREAMBLE_DEFAULT_NO_COMMENT

        if args.postamble is not None:
            POSTAMBLE = args.postamble
        elif OUTPUT_COMMENTS:
            POSTAMBLE = POSTAMBLE_DEFAULT
        else:
            POSTAMBLE = POSTAMBLE_DEFAULT_NO_COMMENT

        if args.inches and (UNITS != UNITS_US_IMP):
            print("Units: US Imperial [inch], check your UC-CNC profile.")
            UNITS = UNITS_US_IMP
            UNIT_FORMAT = UNIT_FORMAT_US_IMP
            UNIT_SPEED_FORMAT = UNIT_SPEED_FORMAT_US_IMP
            UNIT_DEFAULT_CHANGED = True

        if args.metric and (UNITS != UNITS_METRIC):
            print("Units: Metric [mm], check your UC-CNC profile.")
            UNITS = UNITS_METRIC
            UNIT_FORMAT = UNIT_FORMAT_METRIC
            UNIT_SPEED_FORMAT = UNIT_SPEED_FORMAT_METRIC
            UNIT_DEFAULT_CHANGED = True

        if args.modal:
            MODAL = True

        if args.tool_length_offset:
            USE_TLO = True

        if args.repeat:
            REPEAT_ARGUMENTS = True

    except Exception:
        return False

    return True


def append0(line):
    result = line
    if trace_gcode:
        print("export: >>" + result)
    return result


def append(line):
    result = linenumber() + line
    if trace_gcode:
        print("export: >>" + result)
    return result


def export(objectslist, filename, argstring):
    if not processArguments(argstring):
        print("export: process arguments failed, '{}'".format(argstring))
        return None

    global warnings_count
    global problems_count

    warnings_count = 0
    problems_count = 0

    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print(
                "the object " + obj.Name + " is not a path. Please select only path and Compounds."
            )
            return None

    print("export: postprocessing...")
    gcode = append0("%" + PROG_NAME + "\n")
    if argstring:
        gcode += append("({} {})\n".format(__name__, argstring))

    # write header
    if OUTPUT_HEADER:
        for line in HEADER.format(
            VERSION,
            str(now),
        ).splitlines(False):
            if line:
                gcode += append(line + "\n")

    # Write the preamble
    # G20/G21 not supported by UC-CNC, *always* report the configured units.
    #gcode += append("(Units: '" + UNIT_FORMAT + "' and '" + UNIT_SPEED_FORMAT + "')\n")
    if UNIT_DEFAULT_CHANGED:
        gcode += append("(WARNING: Units default changed, check your UC-CNC profile)\n")
        warnings_count += 1

    if OUTPUT_COMMENTS:
        gcode += append("(preamble: begin)\n")
        # for obj in objectslist:
        #    if isinstance(obj.Proxy, Path.Tool.Controller.ToolController):
        #        gcode += append("(T{}={})\n".format(obj.ToolNumber, item.Name))
        # error: global name 'PathScripts' is not defined
    for line in PREAMBLE.splitlines(False):
        gcode += append(line + "\n")
    if OUTPUT_COMMENTS:
        gcode += append("(preamble: done)\n")

    # write the code body
    for obj in objectslist:

        # pre_op
        if OUTPUT_COMMENTS:
            gcode += append("(operation initialise: %s)\n" % obj.Label)
        for line in PRE_OPERATION.splitlines(True):
            gcode += append(line)

        # Affichage de l'outil utilisé
        if hasattr(obj, "ToolController"):
            tool = obj.ToolController
            if hasattr(tool, "Name"):
                gcode += append("(Outil: {})\n".format(tool.Name))

        # turn coolant on if required
        if hasattr(obj, "CoolantMode"):
            coolantMode = obj.CoolantMode
            if coolantMode == "Mist":
                if OUTPUT_COMMENTS:
                    gcode += append("M7 (coolant: mist on)\n")
                else:
                    gcode += append("M7\n")
            if coolantMode == "Flood":
                if OUTPUT_COMMENTS:
                    gcode += append("M8 (coolant: flood on)\n")
                else:
                    gcode += append("M8\n")

        # process the operation gcode
        if OUTPUT_COMMENTS:
            gcode += append("(operation start: %s)\n" % obj.Label)
        gcode += parse(obj)
        if OUTPUT_COMMENTS:
            gcode += append("(operation done: %s)\n" % obj.Label)

        # post_op
        for line in POST_OPERATION.splitlines(True):
            gcode += append(line)

        # turn coolant off if required
        if hasattr(obj, "CoolantMode"):
            coolantMode = obj.CoolantMode
            if not coolantMode == "None":
                if OUTPUT_COMMENTS:
                    gcode += append("M9 (coolant: off)\n")
                else:
                    gcode += append("M9\n")
        if OUTPUT_COMMENTS:
            gcode += append("(operation finalised: %s)\n" % obj.Label)

    # do the post_amble
    if OUTPUT_COMMENTS:
        gcode += append("(postamble: begin)\n")
    for line in POSTAMBLE.splitlines(True):
        gcode += append(line)
    if OUTPUT_COMMENTS:
        gcode += append("(postamble: done)\n")

    # Show the results
    if SHOW_EDITOR:
        dia = PostUtils.GCodeEditorDialog()
        dia.editor.setText(gcode)
        result = dia.exec_()
        if result:
            final = dia.editor.toPlainText()
        else:
            final = gcode
    else:
        final = gcode

    if (0 < problems_count) or (0 < warnings_count):
        print(
            "export: postprocessing: done, warnings: {}, problems: {}, see GCode for details.".format(
                warnings_count, problems_count
            )
        )
    else:
        print("export: postprocessing: done (none of the problems detected).")

    if not filename == "-":
        print("export: writing to '{}'".format(filename))
        gfile = pyopen(filename, "w")
        gfile.write(final)
        gfile.close()

    return final


def linenumber():
    global LINENR

    if LINENR <= 0:
        LINENR = LINE_NUMBER_START
    if OUTPUT_LINE_NUMBERS is True:
        line = LINENR
        LINENR += LINE_NUMBER_STEP
        return "N{:01d} ".format(line)
    return ""

def parse(pathobj):
    out = ""
    lastcommand = None
    precision_string = "." + str(PRECISION) + "f"
    currLocation = {}  # keep track for no doubles

    # The params list control the order of parameters
    params = [
        "X",
        "Y",
        "Z",
        "A",
        "B",
        "C",
        "I",
        "J",
        "K",
        "R",
        "F",
        "S",
        "T",
        "H",
        "L",
        "Q",
    ]
    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters

    if hasattr(pathobj, "Group"):
        # We have a compound or project.

        # if OUTPUT_COMMENTS:
        #    out += linenumber() + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            out += parse(p)
        return out
    else:
        # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        # if OUTPUT_COMMENTS:
        #    out += linenumber() + "(" + pathobj.Label + ")\n"

        for c in PathUtils.getPathWithPlacement(pathobj).Commands:
            commandlist = []  # list of elements in the command, code and params.
            command = c.Name.strip()  # command M or G code or comment string
            commandlist.append(command)

            # if modal: only print the command if it is not the same as the last one
            if MODAL is True:
                if command == lastcommand:
                    commandlist.pop(0)

            if c.Name[0] == "(" and not OUTPUT_COMMENTS:  # command is a comment
                continue

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == "F" and (
                        currLocation[param] != c.Parameters[param] or REPEAT_ARGUMENTS
                    ):
                        if c.Name not in ["G0", "G00"]:  # No F in G0
                            speed = Units.Quantity(c.Parameters["F"], FreeCAD.Units.Velocity)
                            if speed.getValueAs(UNIT_SPEED_FORMAT) > 0.0:
                                commandlist.append(
                                    param
                                    + format(
                                        float(speed.getValueAs(UNIT_SPEED_FORMAT)),
                                        precision_string,
                                    )
                                )
                        else:
                            continue
                    elif param == "T":
                        commandlist.append(param + str(int(c.Parameters["T"])))
                    elif param == "H":
                        commandlist.append(param + str(int(c.Parameters["H"])))
                    elif param == "D":
                        commandlist.append(param + str(int(c.Parameters["D"])))
                    elif param == "S":
                        commandlist.append(param + str(int(c.Parameters["S"])))
                    else:
                        if (
                            (not REPEAT_ARGUMENTS and c.Name not in ["G81", "G82", "G83"])
                            and (param in currLocation)
                            and (currLocation[param] == c.Parameters[param])
                        ):
                            continue
                        else:
                            pos = Units.Quantity(c.Parameters[param], FreeCAD.Units.Length)
                            commandlist.append(
                                param + format(float(pos.getValueAs(UNIT_FORMAT)), precision_string)
                            )

            # store the latest command
            lastcommand = command
            currLocation.update(c.Parameters)

            if "M3" in commandlist:
                out += append(" ".join(commandlist) + "\n")
                out += append("G04 P5000\n")
                commandlist = []

            # Check for Tool Change:
            if command == "M6":
                if TOOL_CHANGEMENT:
                    for line in TOOL_CHANGE.splitlines(True):
                        out += linenumber() + line

                    # add height offset
                    if USE_TLO:
                        tool_height = "\nG43 H" + str(int(c.Parameters["T"]))
                        commandlist.append(tool_height)
                else:
                    commandlist = []

            if command == "message":
                if OUTPUT_COMMENTS is False:
                    out = []
                else:
                    commandlist.pop(0)  # remove the command

            # prepend a line number and append a newline
            if len(commandlist) >= 1:
                if OUTPUT_LINE_NUMBERS:
                    commandlist.insert(0, (linenumber()))

                # append the line to the final output
                for w in commandlist:
                    out += w.strip() + COMMAND_SPACE
                if trace_gcode:
                    print("parse : >>{}".format(out))
                out = out.strip() + "\n"

        return out