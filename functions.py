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
                                     epilog="Palette file must only define the conversion table, as such:\
                                     \n\nFor screen 0:\nRGB 1\n\nFor screen 1:\nRGB 0\nRGB 1\n\nFor graphic modes:\nRGB 0\nRGB 1\n...\nRGB 16\n")
    parser.add_argument("-ip", action="store_true", help="process palette data and include it in output")
    parser.add_argument("-p", help="specify palette file", dest="palette")
    parser.add_argument("-o", help="specify output file", dest="output")
    parser.add_argument("bmp_file")
    parser.add_argument("output_type", choices=["screen0", "screen1", "screen2", "screen3", "screen4", "screen5",\
                                                    "screen6", "screen7", "screen8", "sprite1", "sprite2"])
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
            if len(line[0]) != 3:
                print("error: invalid RGB value in palette")
                exit(0)
            line[1] = int(line[1])
            if line[1] > 15 or line[1] < 0\
                or (argv.output_type == "screen0" and line[1] != 1)\
                or (argv.output_type == "screen1" and (line[1] != 0 and line[1] != 1))\
                or (argv.output_type == "screen6" and (line[1] > 4)):
                print("error: invalid color value in palette")
                exit(1)

    #default palette for screen 0
    elif argv.output_type == "screen0":
        conversion_table = [
            (b'\xFF\xFF\xFF', 1)       #TEXT COLOR
        ]

    #default palette for screen 1
    elif argv.output_type == "screen1":
        conversion_table = [
            (b'\x24\x24\xFF', 0),      #TEXT COLOR 0
            (b'\xFF\xFF\xFF', 1)       #TEXT COLOR 1
        ]

    #default palette for screen 6
    elif argv.output_type == "screen6":
        conversion_table = [
            (b'\x00\x00\x00', 0),      #TRANSPARENT
            (b'\x01\x01\x01', 1),      #BLACK
            (b'\x24\xDB\x24', 2),      #MEDIUM_GREEN
            (b'\x6D\xFF\x6D', 3)       #LIGHT_GREEN
        ]

    #default palette for graphic modes
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
    if argv.output_type == "screen0" and (width != 6 or height != 8):
        print("Screen 0 tile needs to be 6x8")
        exit(2)
    if argv.output_type == "screen1" and (width != height or width != 8):
        print("Screen 1 tile needs to be 8x8")
        exit(2)
    if argv.output_type == "screen2" and (width != height or width != 8):
        print("Screen 2 tile needs to be 8x8")
        exit(2)

    #checking for invalid sprite size
    if argv.output_type == "hwsprite" and (width != height or (width != 8 and width != 16)):
        print("Sprite needs to be 8x8 or 16x16")
        exit(2)

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
        for j in range(0, len(conversion_table)):
            if pixel == conversion_table[j][0]:
                pixel = conversion_table[j][1]
        if type(pixel) is bytes :
            #screen 0: background
            if argv.output_type == "screen0":
                pixel = 0
            #other screens: error
            else:
                print("error: color from outside of palette found: " + str(pixel))
                exit(3)
        pixels.append(pixel)

    return pixels

def write(data):
    switchcase = {
        "screen0" : write_screen0,
        "screen1" : write_screen1,
        "screen2" : write_screens24,
        "screen3" : write_screen3,
        "screen4" : write_screens24,
        "screen5" : write_screen5,
        "screen6" : write_screen6,
        "screen7" : write_screen7,
        "screen8" : write_screen8,
        "sprite1" : write_sprite1,
        "sprite2" : write_sprite2
    }
    write_type = switchcase.get(argv.output_type)
    write_type(data)
    return

def write_screen0(data):
    filename = os.path.splitext(argv.bmp_file)[0]

    #labelling
    pattern = filename + ":\n        db "
    for i in range(0,8):
        line_pattern = 0
        for j in range(0,6):
            line_pattern |= data[j + i * 6]
            line_pattern <<= 1
            if j == 5:
                line_pattern <<= 1
        pattern += "0x{0:0{1}X}".format(line_pattern, 2)
        if i != 7:
            pattern += ','

    if argv.output != None:
        asm = open(argv.output, "w")
    else:
        asm = open(filename + ".asm", "w")
    asm.write(pattern)
    asm.close()

    return

def write_screen1(data):
    filename = os.path.splitext(argv.bmp_file)[0]

    #labelling
    pattern = filename + ":\n        db "
    for i in range(0,8):
        line_pattern = 0
        for j in range(0,8):
            line_pattern |= data[j + i * 8]
            if j != 7:
                line_pattern <<= 1
        pattern += "0x{0:0{1}X}".format(line_pattern, 2)
        if i != 7:
            pattern += ','

    if argv.output != None:
        asm = open(argv.output, "w")
    else:
        asm = open(filename + ".asm", "w")
    asm.write(pattern)
    asm.close()

    return

def write_screens24(data):
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
                    exit(4)
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

def write_screen3(data):
    filename = os.path.splitext(argv.bmp_file)[0]

    #labelling
    pattern = filename + ":\n        db "
    for i in range(0,height//8):
        for j in range(0,width//8):
            top_colors = (data[j * 8 + i * 8 * width] << 4) | data[j * 8 + i * 8 * width + 4]
            bottom_colors = (data[j * 8 + i * 8 * width + 4 * width] << 4) | data[j * 8 + i * 8 * width + 4 * (width + 1)]
            pattern += "0x{0:0{1}X}".format(top_colors, 2)
            pattern += ','
            pattern += "0x{0:0{1}X}".format(bottom_colors, 2)
            if j != (width//8 - 1):
                pattern += ','
            elif i != (height//8 - 1):
                pattern += "\n        db "

    if argv.output != None:
        asm = open(argv.output, "w")
    else:
        asm = open(filename + ".asm", "w")
    asm.write(pattern)
    asm.close()

    return

def write_screen5(data):
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
        if (i + 1) % width != 0:
            dot2 = data[i + 1]
            i += 1
        i += 1
        asm.write("0x{0:0{1}X}".format(((dot2 | (dot1 << 4))), 2))

        #comma between values
        if i % width != 0:
            asm.write(",")

    asm.close()
    return

def write_screen6(data):
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
        dot3 = 0
        dot4 = 0
        j = 0
        if (i + 1) % width != 0:
            dot2 = data[i + 1]
            j += 1
        if (i + 1) % width != 0 and (i + 2) % width != 0:
            dot3 = data[i + 2]
            j += 1
        if (i + 1) % width != 0 and (i + 2) % width != 0 and (i + 3) % width != 0:
            dot4 = data[i + 3]
            j += 1
        i += 1 + j
        asm.write("0x{0:0{1}X}".format((dot4 | (dot3 << 2) | (dot2 << 4) | (dot1 << 6)), 2))

        #comma between values
        if i % width != 0:
            asm.write(",")

    asm.close()
    return

def write_screen7(data):
    return

def write_screen8(data):
    return

def write_sprite1(data):
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
                        exit(5)
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
        print("warning: empty sprite")
    else:
        color += "0x{0:0{1}X}".format(colorvalue[0], 2)
        asm.write(color)
    asm.close()

    return

def write_sprite2(data):
    filename = os.path.splitext(argv.bmp_file)[0]

    #labelling
    pattern = filename + ":\n        db "
    color = filename + "_colors:\n        db "

    for i in range(0,width * height // 64):
        for j in range(0,8):
            line_pattern = 0
            colorvalue = []
            for k in range(0,8):
                pixel = data[k + j * width + (i % 2) * 128 + (i // 2) * 8]
                if pixel != 0:
                    if len(colorvalue) == 0:
                        colorvalue.append(pixel)
                    elif colorvalue[0] != pixel:
                        print("Sprites must have only one color per line")
                        exit(6)
                    line_pattern |= 1
                if k != 7:
                    line_pattern <<= 1
            pattern += "0x{0:0{1}X}".format(line_pattern, 2)
            if len(colorvalue) == 0:
                color += "0x00"
            else:
                color += "0x{0:0{1}X}".format(colorvalue[0], 2)
            if j != 7:
                pattern += ','
                color += ','
        if i != width * height / 64 - 1:
            pattern += "\n        db "
            color += "\n        db "
    if (width * height // 64) != 1:
        color_lines = color.splitlines()
        if color_lines[1] != color_lines[3] or color_lines[2] != color_lines[4]:
            print("Sprites must have only one color per line")
        color = color_lines[0] + '\n' + color_lines[1] + '\n' + color_lines[2]
    if argv.output != None:
        asm = open(argv.output, "w")
    else:
        asm = open(filename + ".asm", "w")

    asm.write(pattern + '\n')
    asm.write(color)
    asm.close()

    return

def write_sif(data):
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
