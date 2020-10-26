import json
with open("256colourto24bit.json", "r") as f:
    colour_translation = json.loads(f.read())

def c256torgb(c):
    n = int(colour_translation[str(c)][2:], 16)
    r = (n >> 16) & 0xFF
    g = (n >>  8) & 0xFF
    b = (n >>  0) & 0xFF
    return r,g,b
    

def read_until(char, data, pos):
    start = pos
    while data[pos] != char: pos += 1
    return data[start:pos], pos
    
def is_24bit(data):
    pos = 0
    while ord(data[pos]) != 27 and pos < len(data) - 7 and data[pos + 1] != "[": pos += 1
    if pos == len(data) - 8: return None
    first_num, pos = read_until(";", data, pos + 2)
    second_num, pos = read_until(";", data, pos + 1)
    if second_num == "2": return True
    if second_num == "5": return False
    return None

def makeData(data):
    out = []
    pos = 0
    bg = (0, 0, 0)
    fg = (255, 255, 255)

    while pos < len(data):
        if ord(data[pos]) == 27:
            pos += 2
            if data[pos:pos + 2] == "0m": #reset code
                bg = (0, 0, 0)
                fg = (255, 255, 255)
                pos += 2
                continue
            first_num, pos = read_until(";", data, pos)
            second_num, pos = read_until(";", data, pos + 1)

            r, pos = read_until(";", data, pos + 1)
            g, pos = read_until(";", data, pos + 1)
            b, pos = read_until("m", data, pos + 1)
            r = int(r)
            g = int(g)
            b = int(b)
            pos += 1
            #print(first_num, second_num, r, g, b)
            if first_num == "38":
                fg = (r, g, b)
            elif first_num == "48":
                bg = (r, g, b)
        else:
            out.append((fg, bg, data[pos]))
            pos += 1
    return out
