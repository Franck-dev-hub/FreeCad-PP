# -*- coding: utf-8 -*-

import FreeCAD
from FreeCAD import Units
import Path
import PathScripts.PathUtils as PathUtils
import argparse
import datetime

import shlex
import Path.Post.Utils as PostUtils
from builtins import open as pyopen

VERSION = "1.4"

TOOLTIP = """ Custom post pro A&F.
"""

PREAMBLE = """
(Header)
G17 G49 G94
G0 G40 G80 G90
G53 Z-1

"""

POSTAMBLE = """(Fin de programme)
G0 G40 G80
M5
G53 Z-1
G53 Y200
M30
"""

# Pre operation text will be inserted before every operation
PRE_OPERATION = """"""

# Post operation text will be inserted after every operation
POST_OPERATION = """"""

# Tool Change commands will be inserted before a tool change
TOOL_CHANGE = """"""

# Name of the G-Code program.
# Set with --name
PROG_NAME = "O1000"

# Set tool length offset.
#Set with --tool-length-offset
USE_TLO = False

# Enable / disable tool changement (M6).
#Set with --tool-changement
TOOL_CHANGEMENT = False

# Number of digits in axis positions
# Set with --precision N
PRECISION = 2

# Metric [mm]
UNITS = "G21"

# Metric [mm]
UNIT_FORMAT = "mm"

# Metric [mm/min]
UNIT_SPEED_FORMAT = "mm/min"


# Arguments
parser = argparse.ArgumentParser(prog=__name__, add_help=False)
parser.add_argument("--name", help="GCode program name")
parser.add_argument("--precision", default="2", help="number of digits of precision, default=2")
parser.add_argument("--tool-length-offset", action="store_true", help="suppress tool length offset G43 following tool changes")
parser.add_argument("--tool-changement", action="store_true", help="Enable / disable M6 for tool changement")
TOOLTIP_ARGS = parser.format_help()


# Debug option, trace to screen while processing to see where things break up.
trace_gcode = False

now = datetime.datetime.now()

LINENR = 0
COMMAND_SPACE = " "
UNIT_DEFAULT_CHANGED = False

# counting warnings and problems.
# Each warning/problem will appear as a WARNING:/PROBLEM: comment in the GCode output.
warnings_count = 0
problems_count = 0

HEADER = """(Post Pro A&F version {})
({})
"""


def processArguments(argstring):
    global PROG_NAME
    global USE_TLO
    global PRECISION
    global UNITS
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT
    global UNIT_DEFAULT_CHANGED

    try:
        UNIT_DEFAULT_CHANGED = False
        args = parser.parse_args(argstring.split())

        if args.name is not None:
            PROG_NAME = args.name

        PRECISION = args.precision

        if args.tool_length_offset:
            USE_TLO = True

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

    # Write header
    for line in HEADER.format(VERSION, str(now)).splitlines(False):
        if line:
            gcode += append(line + "\n")

    # Write the preamble
    for line in PREAMBLE.splitlines(False):
        gcode += append(line + "\n")

    # write the code body
    for obj in objectslist:

        # pre_op
        gcode += append("(Start: %s)\n" % obj.Label)
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
                gcode += append("M7\n")
            if coolantMode == "Flood":
                gcode += append("M8\n")

        # process the operation gcode
        gcode += parse(obj)

        # post_op
        for line in POST_OPERATION.splitlines(True):
            gcode += append(line)

        # turn coolant off if required
        if hasattr(obj, "CoolantMode"):
            coolantMode = obj.CoolantMode
            if not coolantMode == "None":
                gcode += append("M9\n")
        gcode += append("\n")

    # do the post_amble
    for line in POSTAMBLE.splitlines(True):
        gcode += append(line)

    # Show the results
    dia = PostUtils.GCodeEditorDialog()
    dia.editor.setText(gcode)
    result = dia.exec_()
    if result:
        final = dia.editor.toPlainText()
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
        LINENR = 0 # Line number start
    line = LINENR
    LINENR += 1 # Line number step
    return "N{:01d} ".format(line)


def parse(pathobj):
    out = ""
    lastcommand = None
    precision_string = "." + str(PRECISION) + "f"
    currLocation = {}  # keep track for no doubles

    # The params list control the order of parameters
    params = ["X", "Y", "Z", "A", "B", "C", "I", "J", "K", "R", "F", "S", "T", "H", "L", "Q", ]
    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters

    if hasattr(pathobj, "Group"):
        # We have a compound or project.

        for p in pathobj.Group:
            out += parse(p)
        return out
    else:
        # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        skip_origin = True

        for c in PathUtils.getPathWithPlacement(pathobj).Commands:
            commandlist = []  # list of elements in the command, code and params.
            command = c.Name.strip()  # command M or G code or comment string
            commandlist.append(command)

            # Only print the command if it is not the same as the last one
            if command == lastcommand:
                commandlist.pop(0)

            if c.Name[0] == "(":  # command is a comment
                continue

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == "F" and (currLocation[param] != c.Parameters[param]):
                        if c.Name not in ["G0", "G00"]:  # No F in G0
                            speed = Units.Quantity(c.Parameters["F"], FreeCAD.Units.Velocity)
                            if speed.getValueAs(UNIT_SPEED_FORMAT) > 0.0:
                                commandlist.append(param + format(float(speed.getValueAs(UNIT_SPEED_FORMAT)), precision_string))
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
                        if ((c.Name not in ["G81", "G82", "G83"])
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

            # Skip G0 X0.00 Y0.00 Z
            if skip_origin and command == ("G0" or "G00") and "X" in c.Parameters and c.Parameters["X"] == 0.00 and "Y" in c.Parameters and c.Parameters["Y"] == 0.00 and "Z" in c.Parameters:
                skip_origin = False
                continue

            if "M3" in commandlist:
                out += append(" ".join(commandlist) + "\n")
                out += append("G4 P10000\n")
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
                out = []

            # prepend a line number and append a newline
            if len(commandlist) >= 1:
                commandlist.insert(0, (linenumber()))

                # append the line to the final output
                for w in commandlist:
                    out += w.strip() + COMMAND_SPACE
                if trace_gcode:
                    print("parse : >>{}".format(out))
                out = out.strip() + "\n"

        return out