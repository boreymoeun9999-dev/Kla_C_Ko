from pathlib import Path

from PIL import Image, ImageDraw


OUTPUT_DIR = Path(__file__).parent / "png"
SIZE = 512
OUTLINE = "#25334A"
ORANGE = "#F79436"
CREAM = "#FFF4DE"
BLUE = "#4BA9E8"
PINK = "#F28FA0"
WHITE = "#FFFFFF"


def new_canvas(size=SIZE):
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def tiger_face():
    image = new_canvas()
    draw = ImageDraw.Draw(image)

    draw.ellipse((54, 62, 195, 217), fill=ORANGE, outline=OUTLINE, width=12)
    draw.ellipse((317, 62, 458, 217), fill=ORANGE, outline=OUTLINE, width=12)
    draw.ellipse((82, 96, 169, 185), fill="#F7B6A0", outline=OUTLINE, width=8)
    draw.ellipse((343, 96, 430, 185), fill="#F7B6A0", outline=OUTLINE, width=8)
    draw.ellipse((50, 104, 462, 476), fill=ORANGE, outline=OUTLINE, width=14)

    # Broad, rounded stripes keep the markings legible at small UI sizes.
    draw.polygon([(112, 119), (167, 132), (134, 202), (99, 184)], fill=OUTLINE)
    draw.polygon([(400, 119), (345, 132), (378, 202), (413, 184)], fill=OUTLINE)
    draw.polygon([(229, 99), (283, 99), (264, 174), (247, 174)], fill=OUTLINE)
    draw.polygon([(75, 262), (142, 248), (158, 285), (82, 307)], fill=OUTLINE)
    draw.polygon([(437, 262), (370, 248), (354, 285), (430, 307)], fill=OUTLINE)

    draw.ellipse((132, 211, 224, 313), fill=WHITE, outline=OUTLINE, width=8)
    draw.ellipse((288, 211, 380, 313), fill=WHITE, outline=OUTLINE, width=8)
    draw.ellipse((161, 236, 211, 294), fill=BLUE)
    draw.ellipse((303, 236, 353, 294), fill=BLUE)
    draw.ellipse((178, 245, 201, 286), fill=OUTLINE)
    draw.ellipse((316, 245, 339, 286), fill=OUTLINE)
    draw.ellipse((180, 247, 192, 259), fill=WHITE)
    draw.ellipse((318, 247, 330, 259), fill=WHITE)

    draw.ellipse((126, 326, 269, 423), fill=CREAM)
    draw.ellipse((243, 326, 386, 423), fill=CREAM)
    draw.polygon([(219, 326), (293, 326), (256, 359)], fill="#704B4D")
    draw.arc((195, 344, 257, 411), 5, 100, fill=OUTLINE, width=8)
    draw.arc((255, 344, 317, 411), 80, 175, fill=OUTLINE, width=8)
    draw.arc((207, 363, 305, 431), 5, 175, fill=OUTLINE, width=8)
    return image


def cow_face():
    image = new_canvas()
    draw = ImageDraw.Draw(image)

    draw.ellipse((92, 55, 190, 181), fill="#F6D078", outline=OUTLINE, width=10)
    draw.ellipse((322, 55, 420, 181), fill="#F6D078", outline=OUTLINE, width=10)
    draw.ellipse((53, 120, 459, 474), fill=WHITE, outline=OUTLINE, width=14)
    draw.ellipse((109, 137, 176, 190), fill=OUTLINE)
    draw.ellipse((341, 137, 408, 190), fill=OUTLINE)

    draw.ellipse((143, 215, 231, 309), fill=WHITE, outline=OUTLINE, width=8)
    draw.ellipse((281, 215, 369, 309), fill=WHITE, outline=OUTLINE, width=8)
    draw.ellipse((174, 240, 211, 288), fill=OUTLINE)
    draw.ellipse((300, 240, 337, 288), fill=OUTLINE)
    draw.ellipse((181, 244, 193, 256), fill=WHITE)
    draw.ellipse((307, 244, 319, 256), fill=WHITE)

    draw.ellipse((146, 307, 366, 434), fill=PINK, outline=OUTLINE, width=10)
    draw.ellipse((190, 347, 220, 384), fill="#B85869")
    draw.ellipse((292, 347, 322, 384), fill="#B85869")
    draw.line((224, 397, 256, 414, 288, 397), fill=OUTLINE, width=8)
    return image


def combined_badge(tiger, cow):
    image = new_canvas(640)
    draw = ImageDraw.Draw(image)
    draw.ellipse((18, 18, 622, 622), fill="#E8EBEF", outline="#AAB2BE", width=16)
    draw.ellipse((39, 39, 601, 601), fill="#FAFBFC", outline=WHITE, width=8)
    tiger_icon = tiger.resize((390, 390), Image.Resampling.LANCZOS)
    cow_icon = cow.resize((390, 390), Image.Resampling.LANCZOS)
    image.alpha_composite(tiger_icon, (35, 142))
    image.alpha_composite(cow_icon, (215, 142))
    return image


def board_tile():
    image = Image.new("RGBA", (128, 128), "#F6F7F8")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 63, 63), fill="#E9ECEF")
    draw.rectangle((64, 64, 127, 127), fill="#E9ECEF")
    return image


def selection_frame():
    image = new_canvas(128)
    draw = ImageDraw.Draw(image)
    color = "#AEB6C1"
    width = 12
    length = 34
    gap = 18
    for left, top, right, bottom in (
        (gap, gap, gap + length, gap),
        (gap, gap, gap, gap + length),
        (128 - gap, gap, 128 - gap - length, gap),
        (128 - gap, gap, 128 - gap, gap + length),
        (gap, 128 - gap, gap + length, 128 - gap),
        (gap, 128 - gap, gap, 128 - gap - length),
        (128 - gap, 128 - gap, 128 - gap - length, 128 - gap),
        (128 - gap, 128 - gap, 128 - gap, 128 - gap - length),
    ):
        draw.line((left, top, right, bottom), fill=color, width=width)
    return image


def button(icon):
    image = new_canvas(256)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((14, 14, 242, 242), radius=54, fill="#223451")
    if icon == "close":
        draw.line((89, 89, 167, 167), fill=WHITE, width=18)
        draw.line((167, 89, 89, 167), fill=WHITE, width=18)
    else:
        draw.arc((70, 69, 187, 187), 42, 315, fill=WHITE, width=17)
        draw.polygon([(74, 57), (119, 66), (83, 99)], fill=WHITE)
    return image


def score_badge():
    image = new_canvas(256)
    draw = ImageDraw.Draw(image)
    draw.ellipse((14, 14, 242, 242), fill="#E9ECEF", outline="#AAB2BE", width=10)
    draw.ellipse((32, 32, 224, 224), outline=WHITE, width=8)
    return image


def save_png(name, image):
    image.save(OUTPUT_DIR / name, optimize=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tiger = tiger_face()
    cow = cow_face()

    save_png("tiger_face.png", tiger)
    save_png("cow_face.png", cow)
    save_png("tiger_cow_badge.png", combined_badge(tiger, cow))
    save_png("board_tile.png", board_tile())
    save_png("selection_frame.png", selection_frame())
    save_png("restart_button.png", button("restart"))
    save_png("close_button.png", button("close"))
    save_png("score_badge.png", score_badge())


if __name__ == "__main__":
    main()
