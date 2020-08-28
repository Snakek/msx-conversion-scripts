import sys
import os
import argparse

#global variables
width = None
height = None
argv = None

def parse_input():
    global argv
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Converts a bmp into assembly code or a SIF file.",
                                     epilog="Palette file must only define the conversion table, as such:\n\nRGB 0\nRGB 1\n...\nRGB 16\n")
    parser.add_argument("-i", action="store_true", help="process palette data and include it in output")
    parser.add_argument("-p", help="specify palette file", dest="palette")
    parser.add_argument("-o", help="specify output file", dest="output")
    parser.add_argument("bmp_file")
    parser.add_argument("output_type", choices=["screen2", "screen5", "hwsprite"])
    parser.add_argument("format", choices=["asm", "sif"])
    argv = parser.parse_args()

    return

def get_conversion_table():
    #user defined palette
    if argv.palette != None:
        palette = open(sys.argv[2], "r")
        conversion_table = []
        for line in palette:
            conversion_table.append(line.split())
        for line in conversion_table:
            line[0] = bytearray.fromhex(line[0])
            line[1] = int(line[1])

    #default palette
    else:
        conversion_table = [
            (b'\x00\x00\x00', 0),      #TRANSPARENT
            (b'\x01\x01\x01', 1),      #BLACK
            (b'\x24\xDB\x24', 2),      #MEDIUM_GREEN
            (b'\x6D\xFF\x6D', 3),      #LIGHT_GREEN
            (b'\x24\x24\xFF', 4),      #DARK_BLUE
            (b'\x49\x6D\xFF', 5),      #LIGHT_BLUE
            (b'\xB6\x24\x24', 6),      #DARK_RED
            (b'\x49\xDB\xFF', 7),      #CYAN
            (b'\xFF\x24\x24', 8),      #MEDIUM_RED
            (b'\xFF\x6D\x6D', 9),      #LIGHT_RED
            (b'\xDB\xDB\x24', 10),     #DARK_YELLOW
            (b'\xDB\xDB\x92', 11),     #LIGHT_YELLOW
            (b'\x24\x92\x24', 12),     #DARK_GREEN
            (b'\xDB\x49\xB6', 13),     #MAGENTA
            (b'\xB6\xB6\xB6', 14),     #GRAY
            (b'\xFF\xFF\xFF', 15)      #WHITE
        ]

    return conversion_table

def read_bmp():
    global width
    global height
    bmp = open(argv.bmp_file, "rb")

    #reading header
    bmp.seek(10)
    start = bmp.read(4)
    start = int.from_bytes(start, "little")
    bmp.seek(18)
    width = bmp.read(4)
    width = int.from_bytes(width, "little")
    height = bmp.read(4)
    height = int.from_bytes(height, "little")

    #checking for invalid tile size
    if argv.output_type == "screen2" and (width != height or width != 8):
        print("Tile needs to be 8x8")
        exit(0)

    #checking for invalid sprite size
    if argv.output_type == "hwsprite" and (width != height or (width != 8 and width != 16)):
        print("Sprite needs to be 8x8 or 16x16")
        exit(1)

    #reading rgb data
    bmp.seek(start)
    data = []
    byte = bmp.read(1)
    while byte != b'':
        data.append(byte)
        byte = bmp.read(1)

    bmp.close()
    return data

def convert(conversion_table, bmp_data):
    padding = (4 - (width * 3) % 4) % 4
    pixels = []
    for i in range(0, width * abs(height), 1):
        if height > 0:
            pixel = b"".join([bmp_data[((height - 1 - 2 * (i // width)) * width + i) * 3 + (height - 1 - i // width) * padding + 2],
                              bmp_data[((height - 1 - 2 * (i // width)) * width + i) * 3 + (height - 1 - i // width) * padding + 1],
                              bmp_data[((height - 1 - 2 * (i // width)) * width + i) * 3 + (height - 1 - i // width) * padding]])
        else:
            pixel = b"".join([bmp_data[i * 3 + (i // width) * padding + 2],
                              bmp_data[i * 3 + (i // width) * padding + 1],
                              bmp_data[i * 3 + (i // width) * padding]])
        for j in range(0, 16):
            if pixel == conversion_table[j][0]:
                pixel = conversion_table[j][1]
        if type(pixel) is bytes:
            print("error: color from outside of palette found: " + str(pixel))
            exit(2)
        pixels.append(pixel)

    return pixels

def write(data):
    switchcase = {
        "asm" : write_asm,
        "sif" : write_sif
    }
    write_format = switchcase.get(argv.format)
    write_format(data)
    return

def write_asm(data):
    switchcase = {
        "screen2" : write_asm_screen2,
        "screen5" : write_asm_screen5,
        "hwsprite" : write_asm_hwsprite
    }
    write_asm_type = switchcase.get(argv.output_type)
    write_asm_type(data)

def write_sif(data):
    switchcase = {
        "screen2" : write_sif_screen2,
        "screen5" : write_sif_screen5,
        "hwsprite" : write_asm_hwsprite
    }
    write_sif_type = switchcase.get(argv.output_type)
    write_sif_type(data)

def write_asm_screen2(data):
    filename = os.path.splitext(argv.bmp_file)[0]

    #labelling
    pattern = filename + ":\n        db "
    colors = filename + "_colors:\n        db "
    for i in range(0,8):
        line_pattern = 0
        line_colors = []
        for j in range(0,8):
            pixel = data[j + i * 8]
            if line_colors.count(pixel) == 0:
                if len(line_colors) == 2:
                    print("Tiles must have only two colors per line.")
                    exit(3)
                line_colors.append(pixel)
            if len(line_colors) == 2 and pixel == line_colors[1]:
                line_pattern |= 1
            if j != 7:
                line_pattern <<= 1
        if len(line_colors) == 1:
            line_colors.append(0)
        pattern += "0x{0:0{1}X}".format(line_pattern, 2)
        colors += "0x{0:0{1}X}".format((line_colors[1] << 4) | line_colors[0], 2)
        if i != 7:
            pattern += ','
            colors += ','

    if argv.output != None:
        asm = open(argv.output, "w")
    else:
        asm = open(filename + ".asm", "w")
    asm.write(pattern + '\n' + colors)
    asm.close()

    return

def write_asm_screen5(data):
    filename = os.path.splitext(argv.bmp_file)[0]
    if argv.output != None:
        asm = open(argv.output, "w")
    else:
        asm = open(filename + ".asm", "w")

    #labelling
    asm.write(filename + ":")

    i = 0
    while i < len(data):
        #newline
        if i % width == 0:
            asm.write("\n       db ")

        #writing byte from nibbles
        dot1 = data[i]
        dot2 = 0
        if i == 0 or (i + 1) % width != 0:
            dot2 = data[i + 1]
            i += 1
        i += 1
        asm.write("0x{0:0{1}X}".format(((dot2 | (dot1 << 4))), 2))

        #comma between values
        if i % width != 0:
            asm.write(",")

    asm.close()
    return

def write_asm_hwsprite(data):
    filename = os.path.splitext(argv.bmp_file)[0]

    #labelling
    pattern = filename + ":\n        db "
    color = filename + "_color:\n        db "

    colorvalue = []

    for i in range(0,width * height // 64):
        for j in range(0,8):
            line_pattern = 0
            for k in range(0,8):
                pixel = data[k + j * width + (i % 2) * 128 + (i // 2) * 8]
                if pixel != 0:
                    if len(colorvalue) == 0:
                        colorvalue.append(pixel)
                    elif colorvalue[0] != pixel:
                        print("Sprites must have only one color")
                        exit(4)
                    line_pattern |= 1
                if k != 7:
                    line_pattern <<= 1
            pattern += "0x{0:0{1}X}".format(line_pattern, 2)
            if j != 7:
                pattern += ','
        if i != width * height / 64 - 1:
            pattern += "\n        db "

    if argv.output != None:
        asm = open(argv.output, "w")
    else:
        asm = open(filename + ".asm", "w")

    asm.write(pattern + '\n')
    if len(colorvalue) == 0:
        print("Warning: empty sprite")
    else:
        color += "0x{0:0{1}X}".format(colorvalue[0], 2)
        asm.write(color)
    asm.close()

    return

def write_sif_screen2(data):
    return

def write_sif_screen5(data):
    filename = os.path.splitext(argv.bmp_file)[0]
    if argv.output != None:
        sif = open(argv.output, "wb")
    else:
        sif = open(filename + ".sif", "wb")

    #writing header
    sif.write("SIF".encode("ascii"))
    sif.write((width + width % 2).to_bytes(2, "little"))
    sif.write(abs(height).to_bytes(2, "little"))

    i = 0
    while i < len(data):
        dot1 = data[i]
        dot2 = 0
        if i == 0 or (i + 1) % width != 0:
            dot2 = data[i + 1]
            i += 1
        i += 1
        sif.write((dot2 | (dot1 << 4)).to_bytes(1, "little"))

    sif.close()
    return

def write_sif_hwsprites(data):
    return
