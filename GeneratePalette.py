import os, os.path
import sys
import itertools
import hashlib
import time
from datetime import datetime, timezone
from gooey import Gooey, GooeyParser

sys.path.insert(1, 'Base/')
from GamePalette import PaletteColor, DEFAULT_PALETTE_LENGTH, BYTES_PER_COLOR
from GameRoster import GameRoster, BUTTON_A, BUTTON_B, BUTTON_C, BUTTON_D, BUTTONS

DEFAULT_TOLERANCE = 2
MIN_TOLERANCE, MAX_TOLERANCE = 0, 3 # any higher than this and generated colors start to conflict w/each other
BLACK = PaletteColor(0, 0, 0, 255)
TRANSPARENCY = PaletteColor(0, 0, 0, 0)
# colors that should NOT appear in any generated palettes,
# in order to avoid blending in with the background,
# ingame effects (e.g., hit sparks), or hitbox overlays
# https://github.com/odabugs/kof-combo-hitboxes/blob/master/default.ini
RAW_COLORS_TO_AVOID = (
    (  0,   0,   0), # black; background, gauge overlay borders
    # colors used by hitbox overlay
    (255, 255, 255), # white; pivot axes, throwable box
    (  0,   0, 255), # blue; vulnerable box
    (127, 127, 255), # light blue; counter/anywhere vulnerable box
    (160, 160, 255), # lighter blue; OTG vulnerable box
    (255,   0,   0), # red; attack box, close normal range marker
    (  0, 255, 255), # cyan; guard box
    (255, 128,   0), # orange; projectile vulnerable box
    (255,   0, 255), # magenta; throw box
    (  0, 255,   0), # lime green; collision box, close normal range marker
    (255, 176, 144), # peach; stun gauge overlay
    #(160, 192, 224), # azure; guard gauge overlay (98UM only)
)
COLORS_TO_AVOID = tuple(PaletteColor(*color) for color in RAW_COLORS_TO_AVOID)
# set all of these extra palettes to solid black (but don't include them in the inverse mapping file)
EXTRA_PALETTES_TO_BLANK = [
    "Lin Poison Effect",
    "Main Fire Effect",
    "Main Orochi Fire Effect",
    "Orochi Burn Effect",
    "Frozen Effect",
    "MAX Mode and SDM Flash",
    "MAX Flash",
    "MAX2 Flash",
]

def rainbowPaletteGenerator(colorsToAvoid=COLORS_TO_AVOID):
    # generate every possible color in 02UM's RGB555 palette in an endless loop...
    def rawGenerator():
        initialColor = 0xFFFF
        color = initialColor
        outputColor = PaletteColor()
        priorOutputColor = PaletteColor()
        outputColor.setColorFromInt16(color)
        priorOutputColor.setColorFromInt16(color)
        while True:
            yield outputColor
            # avoid generating the exact same color twice in a row
            while outputColor.getColorAsInt16() == priorOutputColor.getColorAsInt16():
                color -= 1
                outputColor.setColorFromInt16(color)
                if color <= 0x8000:
                    color = initialColor # loop back to the beginning
                    raise Exception("Color generator looped back to the start!") # should never be seen
            priorOutputColor.setColorFromARGB32(outputColor.getColorAsARGB32())
    def colorFilter(color):
        return any(color == colorToAvoid for colorToAvoid in colorsToAvoid)
    # ...but skip over colors in the list of colors to avoid
    return itertools.filterfalse(colorFilter, rawGenerator())

# for generating palettes with one solid color (e.g., black to make objects disappear entirely)
def solidColorPaletteGenerator(color):
    return itertools.repeat(color)

def printColorMapping(fromColor, toColor, outputRBGA=False):
    fromR, fromG, fromB = fromColor.asRGBTuple()
    toR, toG, toB, toA = toColor.asRGBATuple()
    if outputRBGA:
        result = "rgb({:>3}, {:>3}, {:>3}) : rgba({:>3}, {:>3}, {:>3}, {:>3})".format(
            fromR, fromG, fromB, # old color (RGB)
            toR, toG, toB, toA   # new color (RGBA)
        )
    else:
        result = "rgb({:>3}, {:>3}, {:>3}) : rgb({:>3}, {:>3}, {:>3})".format(
            fromR, fromG, fromB, # old color (RGB)
            toR, toG, toB        # new color (RGB)
        )
    return result

def generatePalette(inFileName, outFileName, inverseMappingFileName, tolerance=0):
    inverseMappingFileContent = []
    inverseMappingFilePreamble = [
        "# Inverse palette mapping for custom pal_a.bin",
        "# Pass this file as the \"-m\" (or \"--mapping\") parameter when running the \"python ReverseColors.py\" script.",
        ""
    ]
    allColorsGenerated = set([BLACK.asRGBTuple()])
    rainbow = rainbowPaletteGenerator()
    alwaysBlack = solidColorPaletteGenerator(BLACK)

    def writeColorMapping(fromColor, toColor, outputRGBA=False):
        inverseMappingFileContent.append(printColorMapping(fromColor, toColor, outputRGBA))
    
    def sectionBreak(target=inverseMappingFileContent):
        target.append("")
        target.append("# =====")
        target.append("")

    def grabPaletteSegment(source, length=DEFAULT_PALETTE_LENGTH, step=BYTES_PER_COLOR):
        result = [None for i in range(length * step)]
        index = 0
        for color in itertools.islice(source, length):
            color.write(result, index)
            index += step
        return bytes(result)

    def readPaletteSegment(target, source, oldPaletteSegment=None, tolerance=0):
        #count = target.entryCount
        #start, end = target.offset, target.offset + (count * BYTES_PER_COLOR)
        #print("Writing {}-color palettte segment from 0x{:08X} to 0x{:08X}".format(count, start, end))
        target.read(grabPaletteSegment(source, target.entryCount), 0)
        if oldPaletteSegment is not None:
            for i in range(len(target)):
                rawNewColor = target[i]
                oldColor = oldPaletteSegment[i]
                rawNewColorKey = rawNewColor.asRGBTuple()
                # rawNewColor = newColor.getColorAsInt16()
                rawR, rawG, rawB = rawNewColorKey
                for newR in range(rawR-tolerance, rawR+tolerance+1, 1):
                    for newG in range(rawG-tolerance, rawG+tolerance+1, 1):
                        for newB in range(rawB-tolerance, rawB+tolerance+1, 1):
                            if (0 <= newR <= 255) and (0 <= newG <= 255) and (0 <= newB <= 255):
                                newColor = PaletteColor(newR, newG, newB, 255)
                                newColorKey = newColor.asRGBTuple()
                                if newColorKey not in allColorsGenerated:
                                    allColorsGenerated.add(newColorKey)
                                    writeColorMapping(newColor, oldColor)
                                else:
                                    raise Exception("ERROR: Color {} has already been generated earlier!".format(newColorKey))
                                    # pass
                if tolerance > 0:
                    inverseMappingFileContent.append("") # blank "spacer" between entries in a palette segment
        # end readPaletteSegment()

    def readPaletteSegments(targetSegments, rawSource, oldPaletteSegments=None, tolerance=0):
        logToInverseMapping = (oldPaletteSegments is not None)
        if logToInverseMapping:
            inverseMappingFileContent.append("\n# A button palette segments")
        if type(rawSource) is list: # when reading source colors from palette file
            segmentCount = min(len(targetSegments), len(rawSource))
            sourceSegments = rawSource
        else: # when reading source colors from "live" color generator function
            segmentCount = len(targetSegments)
            sourceSegments = list(itertools.repeat(rawSource, segmentCount))
        for i in range(segmentCount):
            targetSegment = targetSegments[i]
            sourceSegment = sourceSegments[i]
            oldSegment = (oldPaletteSegments is not None and oldPaletteSegments[i] or None)
            start, end = targetSegment.offset, targetSegment.offset + (len(targetSegment) * BYTES_PER_COLOR)
            if logToInverseMapping:
                inverseMappingFileContent.append("\n# A button palette segment {} (0x{:06X} to 0x{:06X}; {} color entries in original palette)".format(
                    i+1, start, end-1, len(targetSegment)
                ))
            readPaletteSegment(targetSegment, sourceSegment, oldSegment, tolerance)
        if logToInverseMapping:
            inverseMappingFileContent.append("# End A button palette segments")
        # end readPaletteSegments()

    def processCharacter(character, tolerance=0):
        inverseMappingFileContent.append("# " + character.name)
        oldCharacter = oldPalette.getCharacterByName(character.name)

        # give each character a gradient A button palette
        paletteA = character.getButtonPalette(BUTTON_A)
        oldPaletteA = oldCharacter.getButtonPalette(BUTTON_A)
        readPaletteSegments(paletteA, rainbow, oldPaletteA, tolerance)
        print("Generated base A button palette for " + character.name)

        # set all character's portrait palattes to solid black (NOT included in inverse mapping)
        for portraitPalettes in character.iterPortraitPalettes():
            readPaletteSegments(portraitPalettes, alwaysBlack)

        # extend the gradient for each of this character's extra palettes, if applicable
        # (don't reuse any colors between the A button and extra palettes for the same character)
        # (preferably don't reuse any colors at all, ever, if it can be avoided)
        extraPalettesGenerated = 0
        for i in range(character.countExtraPalettes()):
            extraPalette = character.getExtraPalette(i)
            oldExtraPalette = oldCharacter.getExtraPalette(i)
            if len(extraPalette) > 0:
                start, end = extraPalette.offset, extraPalette.offset + (len(extraPalette) * BYTES_PER_COLOR)
                inverseMappingFileContent.append("\n# Extra palette segment {} (0x{:06X} to 0x{:06X}; {} color entries)".format(
                    i+1, start, end-1, len(extraPalette)
                ))
                readPaletteSegment(extraPalette, rainbow, oldExtraPalette, tolerance)
                extraPalettesGenerated += 1
        if extraPalettesGenerated > 0:
            print("Generated {} extra palette(s) for {}".format(extraPalettesGenerated, character.name))
        else:
            print(character.name + " has no extra palettes to generate")
        # make each character's B button palette solid black
        paletteB = character.getButtonPalette(BUTTON_B)
        readPaletteSegments(paletteB, alwaysBlack)
        print("Generated base B button palette for " + character.name)
        print("=====")

        inverseMappingFileContent.append("# End " + character.name)
        sectionBreak() # blank lines between characters
        # end processCharacter()

    # start main block of generatePalette()
    print("Reading input palette file: " + inFileName)
    print("====")
    with open(inFileName, "rb") as inFile:
        oldPaletteRaw = inFile.read()
        oldPalette = GameRoster(oldPaletteRaw)
        newPalette = GameRoster(oldPaletteRaw)

    # set character palettes
    for character in newPalette:
        processCharacter(character, tolerance)
    
    # set select "extra" palettes (e.g., for special hit effects) to solid black
    # (these don't go in the inverse mapping file)
    for paletteName in EXTRA_PALETTES_TO_BLANK:
        palette = newPalette.getExtraPaletteByName(paletteName)
        readPaletteSegment(palette, alwaysBlack)
        print("Generated special palette for \"{}\" (NOT included in inverse palette mapping)".format(paletteName))
    
    # make black transparent in the inverse mapping file
    # (every other color in the file should be opaque)
    inverseMappingFileContent.append("# Transparency")
    writeColorMapping(BLACK, TRANSPARENCY, True)

    newPaletteRaw = list(oldPaletteRaw)
    newPalette.write(newPaletteRaw)
    newPaletteRaw = bytes(newPaletteRaw)
    oldHash = hashlib.sha1(oldPaletteRaw).hexdigest().upper()
    newHash = hashlib.sha1(newPaletteRaw).hexdigest().upper()
    inverseMappingFilePreamble.append("# Input palette file SHA-1 hash:  " + oldHash)
    inverseMappingFilePreamble.append("# Output palette file SHA-1 hash: " + newHash)
    inverseMappingFilePreamble.append("# This file contains {} total color mappings.".format(len(allColorsGenerated)))
    inverseMappingFilePreamble.append("# Tolerance value used when generating this file: {}".format(tolerance))

    outPath = os.path.dirname(outFileName)
    if not os.path.exists(outPath):
        os.makedirs(outPath)

    with open(outFileName, "wb") as outFile:
        outFile.write(newPaletteRaw)
    print("=====")
    print("Wrote output palette file to: " + outFileName)

    now = datetime.now(timezone.utc).strftime("%B %d, %Y, %I:%M %p UTC")
    inverseMappingFilePreamble.append("# Inverse palette mapping file generated on {}.".format(now))
    sectionBreak(inverseMappingFilePreamble)
    inverseMappingFileContent[:0] = inverseMappingFilePreamble
    with open(inverseMappingFileName, "w") as inverseMappingFile:
        inverseMappingFile.write("\n".join(inverseMappingFileContent))
    print("Wrote inverse palette mapping to: " + inverseMappingFileName)
    return 0
    # end generatePalette()

@Gooey(program_description="Creates non black A and black B palettes for all characters with a key to return to the originals.", default_size=(700, 640), optional_cols=1) 
def main():
    cwd = os.path.abspath(os.getcwd())
    defaultPaletteFileName = "pal_a.bin"
    inversePaletteMappingFileName = "inversePaletteMapping.txt"
    defaultOutputPath = "new_palette"
    
    parser = GooeyParser()
    parser.add_argument("Input Palette Path",
        default=cwd,
        help="Location of input (source) palette files",
        widget="DirChooser"
    )
    parser.add_argument("-o", "--out",
        dest="Output Palette Path",
        default=os.path.join(cwd, defaultOutputPath),
        help="Location to store output palette files and inverse palette mapping",
        widget="DirChooser"
    )
    parser.add_argument("--tolerance",
        type=int,
        dest="Tolerance",
        default=DEFAULT_TOLERANCE,
        help="Amount of variation in source image colors to tolerate when matching output colors (per each R/G/B color channel). Reduce for faster performance but slight chances of color mismatch.",
        # widget="IntegerField"
        widget="Slider",
        gooey_options={
            "min": MIN_TOLERANCE,
            "max": MAX_TOLERANCE,
            "increment": 1,
        }
    )
    parser.add_argument("-d", "--default",
		action="store_true",
		help="Set the current values as the new default configuration.")

    """
    if len(sys.argv) < 2:
        parser.print_help()
        return 1
    else:
    """
    rawArgs = parser.parse_args()
    args = vars(rawArgs) # convert parsed arguments into dict
    inputPaletteFileName = os.path.abspath(os.path.join(args["Input Palette Path"], defaultPaletteFileName))
    outputPaletteFileName = os.path.abspath(os.path.join(args["Output Palette Path"], defaultPaletteFileName))
    inversePaletteMappingFileName = os.path.abspath(os.path.join(args["Output Palette Path"], inversePaletteMappingFileName))
    default = args["default"]
    
    if default == True:
        input = repr(args["Input Palette Path"]) #Convert quotes into double quotes so the address is written later with quotes + deal with escape characters
        output = repr(args["Output Palette Path"])
        tolerance = args["tolerance"]
        data=[input, output, tolerance]
        j=0
        with open("GeneratePalette.py","r") as e:
            new = e.read().splitlines(True) #Grab each line and keep the \n endline character
            e.close()
        for i in range(len(data)):
            while new[j].find("default=") == -1:
                j+=1
            l = new[j].split("default=")
            new_line = l[0] + "default=" + data[i] + ',\n'
            if new[j-1].find('#') == -1 and new[j] != new_line:
                new[j] = '#' + new[j].replace("default=","default(base)=")
                j+=1
                new.insert(j,new_line)
            else:
                new[j] = new_line
            j+=1
        with open("GeneratePalette.py","w") as e:
            e.write(''.join(new))
            e.close()
            
    if os.path.abspath(args["Input Palette Path"]).lower() == os.path.abspath(args["Output Palette Path"]).lower():
        print("WARNING: Input and output file paths are the same.  Output files may not overwrite the input files.  Exiting now.")
        return 1
    else:
        start = time.perf_counter()
        result = generatePalette(inputPaletteFileName, outputPaletteFileName, inversePaletteMappingFileName, args["Tolerance"])
        end = time.perf_counter()
        elapsed = end - start
        print("Generated palette file and inverse color mapping in {:.3f}s".format(elapsed))
        return result

if __name__ == "__main__":
    result = main()
    sys.exit(result)
