from PIL import Image, ImageDraw, ImageFont
from pandas import DataFrame, Series, read_csv
import numpy as np
#from numpy import uint256

class LeaderboardPrinter:
    title_font = "fonts/Monofonto/monofonto.otf"
    heading_font = "fonts/Monofonto/monofonto.otf"
    basic_font = "fonts/Monofonto/monofonto.otf"

    # Set font objects for each type
    t_font = ImageFont.truetype(title_font, 100)
    h_font = ImageFont.truetype(heading_font, 60)
    b_font = ImageFont.truetype(basic_font, 40)

    SOLID_WHITE = (255, 255, 255, 255)
    SOLID_GREY = (128, 128, 128, 255)
    SOLID_BLACK = (0, 0, 0, 255)

    title_pos = (50, 50)
    bg_padding = 150
    headings = ["Rank", "Username", "Total Points"]
    heading_offset = 25
    heading_padding = 10
    row_space = 15
    column_space = 150# 50

    num_rounds = 5

    col_fmts = ["{}", "{:,}"]

    def __init__(self, img_name="PointsLeaderboard.png", match_size=5, leaderboard_size=10):
        self.title = "Betting Leaderboard"
        self.output_path = img_name
        self.match_size = match_size
        self.lb_size = leaderboard_size

    def set_size(self, size: int):
        self.lb_size = size

    def get_background_size(self):
        y_size = 0
        x_size = 0
        # Consider the headings - x
        for heading in self.headings:
            heading_size = self.h_font.getsize(heading)
            x_size += heading_size[0] + self.column_space
        # Consider the title - y
        y_size += self.t_font.getsize("X")[1]
        # Consider the headings - y
        y_size += self.heading_offset
        y_size += self.h_font.getsize("X")[1]
        y_size += self.heading_padding
        # Consider the size of each line on the leaderboard - y
        entry_size = self.b_font.getsize("X")
        y_size += (self.lb_size + 1) * (entry_size[1] + self.row_space)

        title_x, title_y = self.t_font.getsize(self.title)
        if x_size + self.bg_padding < title_x:
            final_x = title_x + self.bg_padding * 2
        else:
            final_x = x_size + self.bg_padding
        return final_x, y_size + self.bg_padding

    def make_background(self, size: tuple) -> Image:
        return Image.new("RGBA", size, self.SOLID_BLACK)

    def draw_title(self, ctxt: Image, title: str, position: tuple) -> None:
        ctxt.text(position, title, font=self.t_font, fill=self.SOLID_WHITE, stroke_width=2, stroke_fill=self.SOLID_BLACK)
        self.underline_text(ctxt, title, position, font=self.t_font, line_width=5)

    def underline_text(self, ctxt: Image, text: str, position: tuple, font=None, line_width=3) -> None:
        underline_offset = 5
        if font:
            object_size = font.getsize(text)
            s_x = position[0]
            e_x = position[0] + object_size[0]
            y = object_size[1] + underline_offset + position[1]
            ctxt.line([(s_x, y), (e_x, y)], fill=self.SOLID_WHITE, width=line_width)

    def draw_headings(self, ctxt: Image, headings: list, start_pos: tuple) -> list:
        x = start_pos[0]
        y = start_pos[1]
        column_positions = list()
        for i, heading in enumerate(headings):
            # they need to be in columns
            text_size = self.h_font.getsize(heading)
            ctxt.text((x, y), heading, font=self.h_font, fill=self.SOLID_WHITE, stroke_width=1, stroke_fill=self.SOLID_BLACK)
            self.underline_text(ctxt, heading, (x, y), font=self.h_font)
            column_positions.append((x, y + text_size[1]))
            x += text_size[0] + self.column_space
        return column_positions

    def draw_entries(self, ctxt: Image, df: DataFrame, col_positions: list, from_pos: int = 0) -> None:
        for rank, (uid, ranking) in enumerate(df.iterrows()):
            offset = self.b_font.getsize("X")[1]
            # Draw rank
            x = col_positions[0][0]
            y = col_positions[0][1] + self.heading_padding + (self.row_space + offset) * rank
            ctxt.text((x, y), repr(rank + 1 + from_pos), font=self.b_font, fill=self.SOLID_WHITE, stroke_width=1, stroke_fill=self.SOLID_BLACK)

            # Draw stick number
            x = col_positions[1][0]
            y = col_positions[1][1] + self.heading_padding + (self.row_space + offset) * rank
            #print("uid: ", uid)
            #print("rank: ", ranking)
            #print(ranking)
            #ctxt.text((x, y), str(uid), font=self.b_font, fill=self.SOLID_WHITE, stroke_width=1, stroke_fill=self.SOLID_BLACK)
            for i, col in enumerate(ranking):
                # If col is the list of fight rounds then do the else (turn rounds into matches)
                #print(i, col)
                #txt = repr(col) if not isinstance(col, str) else col
                if not i and len(col) > 15: # the name column
                    col = col[:15] + "..."
                txt = self.col_fmts[i].format(col)
                #print(txt)
                x = col_positions[i+1][0]
                y = col_positions[i+1][1] + self.heading_padding + (self.row_space + offset) * rank
                ctxt.text((x, y), txt, font=self.b_font, fill=self.SOLID_WHITE, stroke_width=1, stroke_fill=self.SOLID_BLACK)

    def draw_leaderboard(self, df: DataFrame, title="Betting Leaderboard", from_pos: int = 0) -> Image:
        title_size = self.t_font.getsize(title)
        bg_size = self.get_background_size()
        bg = self.make_background(bg_size)
        context = ImageDraw.Draw(bg)
        self.draw_title(context, title, self.title_pos)

        column_positions = self.draw_headings(context,
                                              self.headings,
                                              (50, self.title_pos[1] + title_size[1] + self.heading_offset))
        self.draw_entries(context, df[:self.lb_size], column_positions, from_pos=from_pos)
        return bg

    def make_leaderboard(self, df: DataFrame, title="Betting Leaderboard", from_pos: int = 0) -> None:
        img = self.draw_leaderboard(df, title=title, from_pos=from_pos)
        img.save(self.output_path)

if __name__ == "__main__":
    data = read_csv("user_points.csv")#, dtype={"uid": np.int64, "name": str, "points": np.int64})
    data = data.set_index("uid").sort_values(by="points", ascending=False)
    data["points"] = data["points"].astype(np.uint64)
    print(data)

    n = data.index.get_loc(245119520627228672)
    print(n)

    print(data.index[2:5])


    lbd =LeaderboardPrinter(leaderboard_size=35)
    img = lbd.draw_leaderboard(data)
    img.show()