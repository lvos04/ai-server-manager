# Knipt een verticaal stuk uit een schermafdruk om het leesbaar te bekijken: python3 knip.py in.png uit.png y0 y1
import sys
from PIL import Image
im = Image.open(sys.argv[1]); y0, y1 = int(sys.argv[3]), int(sys.argv[4])
im.crop((0, y0, im.width, min(y1, im.height))).save(sys.argv[2])
print(im.size)
