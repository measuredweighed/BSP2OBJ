import io

from PIL import Image

class ImageLoader(object):
    @staticmethod
    def fromPCX(data):
        stream = io.BytesIO(data)
        img = Image.open(stream).convert("RGB")
        return list(img.getdata())

    @staticmethod
    def fromLMP(data):
        pixels = []
        for i in range(0, len(data), 3):
            r, g, b = struct.unpack('BBB', data[i+0:i+3])
            pixels.append((r, g, b))
        return pixels
