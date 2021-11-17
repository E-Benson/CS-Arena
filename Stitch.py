from PIL import Image, ImageDraw, ImageFont


font = ImageFont.truetype("fonts/Monofonto/monofonto.otf", 55)
vs_font = ImageFont.truetype("fonts/Monofonto/monofonto.otf", 95)
SOLID_WHITE = (255, 255, 255, 255)
SOLID_BLACK = (0, 0, 0, 255)

x_size = 1000
y_size = 1000
title_x_size = x_size
title_y_size = 100



def title_text(text):
    title_bg = Image.new("RGBA", (x_size, 100), SOLID_BLACK)
    ctxt = ImageDraw.Draw(title_bg)
    bg_x, bg_y = title_bg.size
    text_x, text_y = font.getsize(text)
    pos = ((bg_x - text_x) / 2, (bg_y - text_y) / 2)
    ctxt.text(pos, text, font=font, fill=SOLID_WHITE)
    return title_bg


def main_img(img_path1, img_path2):
    img1 = Image.open(img_path1)
    img2 = Image.open(img_path2)
    bg = Image.new("RGBA", (x_size * 2, y_size + title_y_size), SOLID_WHITE)
    bg.paste(img1, (0, 0))
    bg.paste(img2, (x_size, 0))
    return bg


def vs_screen(s1_num, s1_path, s2_num, s2_path):
    bg = main_img(s1_path, s2_path)
    s1_title = title_text(s1_num)
    s2_title = title_text(s2_num)
    bg.paste(s1_title, (0, y_size))
    bg.paste(s2_title, (x_size, y_size))
    return bg

if __name__ == "__main__":
    p1 = "stick_images/1478709095920774922.png"
    p2 = "stick_images/587658754180827773.png"
    #vs = vs_screen("#86", p1, "#914", p2)
   # vs.show()

    vs = Image.new("RGBA", (1900, 1000), SOLID_WHITE)
    s1 = Image.open(p1)
    s2 = Image.open(p2)

    m1 = Image.open("mask1.png").convert(mode="L")
    m2 = Image.open("mask2.png").convert(mode="L")

    #vs.paste(s1, (0,0), m1)
    vs.paste(s2, (1000, 0), m2)

    vs.show()

"""
    v = Image.new("RGBA", (1000, 1000), SOLID_WHITE)
    i = Image.open(p1)
    m = Image.open("mask2.png")
    tmp = Image.new("L", (1000, 1000), 1)
    c = m.convert(mode="L")
    #tmp.paste(c, (0, 0))
    #mask = Image.frombytes("RGBA", i.size, i)
    v.paste(i, (0,0), m)
    v.show()
"""