from PIL import Image, ImageDraw, ImageFont
from pandas import DataFrame, read_csv
from numpy import ceil


class Leaderboard:

    def __init__(self, csv_name="Leaderboard.csv", leaderboard_size=10):
        self.csv_name = csv_name
        self.lb = self.build_leaderboard()
        self.lb_printer = LeaderboardPrinter(leaderboard_size=leaderboard_size)
        base_fname = csv_name.split(".")[0]
        self.png_name = f"{base_fname}.png"

    def build_leaderboard(self) -> DataFrame:
        col_names = ["snum", "wins", "victories", "rounds"]
        try:
            df = read_csv(self.csv_name)

            def clean_list(rds):
                cleaned = "".join([c for c in rds.strip("[]") if c != "'"])
                return cleaned.split(", ")
            df["rounds"] = df["rounds"].apply(clean_list)
            df = df.set_index("snum")
        except FileNotFoundError:
            df = DataFrame(columns=col_names)
            df = df.set_index("snum")
        return df

    def update_leaderboard(self, rounds: list, sticks: list) -> None:
        for stick in sticks:
            wins = sum([1 for _ in rounds if _ == stick])
            victory = 1 if wins >= ceil(len(rounds) / 2) else 0
            stick_data = {
                "snum": stick,
                "wins": wins,
                "victories": victory,
                "rounds": rounds
            }
            try:
                stick_pos = self.lb.loc[stick]
                for col in self.lb.columns:
                    self.lb.at[stick, col] = self.lb.loc[stick][col] + stick_data[col]
            except KeyError:
                self.lb.loc[stick] = stick_data
        self.lb.to_csv(self.csv_name)

    def make_leaderboard(self) -> None:
        sorted_lb = self.lb.sort_values(by=["victories", "wins"], ascending=False)
        lb_image = self.lb_printer.draw_leaderboard(sorted_lb)
        lb_image.save(self.png_name)


class LeaderboardPrinter:
    #title_font = "fonts/Codesaver/CodeSaver.otf"
    #heading_font = "fonts/Codesaver/CodeSaver.otf"
    #basic_font = "fonts/Codesaver/CodeSaver.otf"

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
    bg_padding = 50
    headings = ["Rank", "Stick Number", "Round Wins", "Match Wins", "Total Matches"]
    heading_offset = 25
    heading_padding = 10
    row_space = 15
    column_space = 50

    num_rounds = 5

    def __init__(self, img_name="Leaderboard.png", match_size=5, leaderboard_size=10):
        self.output_path = img_name
        self.match_size = match_size
        self.lb_size = leaderboard_size

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
        return x_size + self.bg_padding, y_size + self.bg_padding

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

    def draw_entries(self, ctxt: Image, df: DataFrame, col_positions: list) -> None:
        for rank, (snum, stick) in enumerate(df.iterrows()):
            offset = self.b_font.getsize("X")[1]
            # Draw rank
            x = col_positions[0][0]
            y = col_positions[0][1] + self.heading_padding + (self.row_space + offset) * rank
            ctxt.text((x, y), repr(rank + 1), font=self.b_font, fill=self.SOLID_WHITE, stroke_width=1, stroke_fill=self.SOLID_BLACK)

            # Draw stick number
            x = col_positions[1][0]
            y = col_positions[1][1] + self.heading_padding + (self.row_space + offset) * rank
            ctxt.text((x, y), snum, font=self.b_font, fill=self.SOLID_WHITE, stroke_width=1, stroke_fill=self.SOLID_BLACK)
            for i, col in enumerate(stick):
                # If col is the list of fight rounds then do the else (turn rounds into matches)
                txt = repr(col) if type(col) != list else repr(len(col) // self.match_size)
                x = col_positions[i + 2][0]
                y = col_positions[i + 2][1] + self.heading_padding + (self.row_space + offset) * rank
                ctxt.text((x, y), txt, font=self.b_font, fill=self.SOLID_WHITE, stroke_width=1, stroke_fill=self.SOLID_BLACK)

    def draw_leaderboard(self, df: DataFrame, title="CryptoStykz Leaderboard") -> Image:
        title_size = self.t_font.getsize(title)
        bg_size = self.get_background_size()
        bg = self.make_background(bg_size)
        context = ImageDraw.Draw(bg)
        self.draw_title(context, title, self.title_pos)

        column_positions = self.draw_headings(context,
                                              self.headings,
                                              (50, self.title_pos[1] + title_size[1] + self.heading_offset))
        self.draw_entries(context, df[:self.lb_size], column_positions)
        return bg


if __name__ == "__main__":
    leaderboard = Leaderboard(leaderboard_size=10)
    lbp = LeaderboardPrinter()
    print(leaderboard.lb)
    s = leaderboard.lb.loc["#1"]
    print(s.loc["rounds"])
    print(s["rounds"])
    leaderboard.make_leaderboard()
    img = lbp.draw_leaderboard(leaderboard.lb)
    img.show()
