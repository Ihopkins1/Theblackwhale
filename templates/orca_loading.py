from PIL import Image, ImageDraw
import imageio
import numpy as np
import os

# Canvas settings
WIDTH = 256
HEIGHT = 144
BG_COLOR = (0, 25, 51)  # Dark ocean blue

# Orca sprite (detailed 8-bit, style B)
# Each pixel is a tuple (R,G,B) or None for transparency
ORCA_SPRITE = [
    [None, None, (0,0,0), (0,0,0), None, None],
    [None, (0,0,0), (255,255,255), (255,255,255), (0,0,0), None],
    [(0,0,0), (255,255,255), (0,0,0), (0,0,0), (255,255,255), (0,0,0)],
    [(0,0,0), (0,0,0), (255,255,255), (255,255,255), (0,0,0), (0,0,0)],
    [None, (0,0,0), (0,0,0), (0,0,0), (0,0,0), None],
    [None, None, (0,0,0), None, None, None],
]

PIXEL_SIZE = 8  # Scale factor for the sprite


def draw_orca(frame, x, y):
   
    draw = ImageDraw.Draw(frame)
    for row_idx, row in enumerate(ORCA_SPRITE):
        for col_idx, color in enumerate(row):
            if color is not None:
                px = x + col_idx * PIXEL_SIZE
                py = y + row_idx * PIXEL_SIZE
                draw.rectangle(
                    [px, py, px + PIXEL_SIZE, py + PIXEL_SIZE],
                    fill=color
                )


def create_frame(x_pos):

    frame = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    y_pos = HEIGHT // 2 - (len(ORCA_SPRITE) * PIXEL_SIZE) // 2
    draw_orca(frame, x_pos, y_pos)
    return frame


def main():
    frames = []
    total_frames = 60

    # Orca width in pixels
    orca_width = len(ORCA_SPRITE[0]) * PIXEL_SIZE

    # Start off-screen left, end off-screen right
    start_x = -orca_width
    end_x = WIDTH

    for i in range(total_frames):
        t = i / total_frames
        x = int(start_x + (end_x - start_x) * t)
        frame = create_frame(x)
        frames.append(np.array(frame))

    # Save GIF animation for compatibility without an MP4 backend
    output_file = "killer_whale_loading.gif"
    imageio.mimsave(output_file, frames, fps=15, format='GIF')

    print(f"Animation saved as {output_file}")


if __name__ == "__main__":
    main()
