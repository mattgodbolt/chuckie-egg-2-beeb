import sys
from PIL import Image
from util import crop, W

names = sys.argv[2:]
ims = [crop(f"{W}/work/scenes/{n}.png") for n in names]
cols = 3
rows = (len(ims) + cols - 1) // cols
m = Image.new("RGB", (cols * 260, rows * 196), (80, 80, 80))
for i, im in enumerate(ims):
    m.paste(im, ((i % cols) * 260, (i // cols) * 196))
m.save(f"{W}/work/{sys.argv[1]}")
