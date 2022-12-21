import os, shutil, subprocess
from settings import Settings
from io import BytesIO
from PIL import Image

class Normalizer:
    def __init__(self, img_path):
        self.img = Image.open(img_path)
        self.img_path = img_path
        self.width, self.height = self.img.size

        self.settings = Settings()
        self.target_dim = self.settings.target_dim
        self.prequantize_limit = self.settings.prequantize_limit
        self.output_path = self.settings.output_dir + '\\' + os.path.splitext(os.path.basename(img_path))[0]

    def normalize(self):
        """Normalizer driver function."""

        # Image is already normalized.
        if (max(self.width, self.height) < self.target_dim and self.width == self.height):
            self.img.close()
            shutil.move(self.img_path, self.settings.output_dir)
            return
        
        if (min(self.width, self.height) > self.target_dim):
            self.resize_image()

        if (self.width != self.height):
            self.pad_image()
            self.save_png()
        else:
            self.save_jpeg()

        self.img.close()

    def resize_image(self):
        """
        Attempts to resize image to a target dimension and target file size. 
        If transparency required (PNG), reduces dimensions in steps of 200 until target file size is met.
        """

        target_dim = self.target_dim

        # The image does not need transparency padding and can be saved as a JPEG.
        # Size is less of a concern and reduction is performed with other tools.
        if (self.width == self.height):
            self.img.thumbnail((target_dim, target_dim), resample = Image.Resampling.LANCZOS)
            return

        # Result image needs transparency padding and must be stored as PNG.
        while True:
            temp_img = self.img.copy()
            temp_img.thumbnail((target_dim, target_dim), resample = Image.Resampling.LANCZOS)

            temp_store = BytesIO()
            temp_img.save(temp_store, 'png', optimize = True)

            temp_store_size_KB = int(temp_img.tell() / 1024)

            if (temp_store_size_KB < self.prequantize_limit):
                self.img = temp_img
                return
            else:
                target_dim -= 200

    def pad_image(self):
        """Pads non 1:1 aspect ratio image with transparency."""

        canvas_dim = max(self.width, self.height)

        img_pad = Image.new('RGBA', (canvas_dim, canvas_dim), (0, 0, 0, 0))
        
        if (self.width > self.height):
            img_pad.paste(self.img, (0, (self.width - self.height) // 2))
        else:
            img_pad.paste(self.img, ((self.height - self.width) // 2), 0)

        self.img = img_pad

    def save_png(self):
        """Saves the image as a PNG file."""

        self.img.save(self.output_path + '.png', optimize = True)

    def save_jpeg(self):
        """Saves the image as a JPEG file."""

        self.img.save(self.output_path + '.jpeg', optimize = True, quality = 'keep')

class Compressor:
    def __init__(self, img_path) -> None:
        self.img_path = img_path
        self.ext = os.path.splitext(img_path)[1]

    def compress(self):
        if (self.ext == '.png'):
            self.quantize_image()
            self.optipng()
        elif (self.ext == '.jpeg'):
            self.jpegoptim()

    def quantize_image(self):
        """Quantizes PNG files to 8bit colour space."""

        settings = Settings()

        subprocess.run(['pngquant.exe', '--force', '--ext=.png', '--speed=%d' % (settings.speed), '--floyd=%d' % (settings.floyd), self.img_path])

    def optipng(self):
        """Lossless PNG compression. Reduces size of IDAT data stream."""

        subprocess.run(['optipng.exe', '-silent', self.img_path])

    def jpegoptim(self):
        """Lossless JPEG Compression. Optimizes Huffman tables."""

        subprocess.run(['jpegoptim.exe', '--quiet', '--strip-all', self.img_path])

def batch_process():
    """Processes all images in a given directory."""

    settings = Settings()
    valid_ext = settings.valid_ext

    to_process = [file for file in os.listdir(settings.input_dir) if os.path.splitext(file)[1] in valid_ext]

    for img in to_process:
        img_edit = Normalizer(settings.input_dir + '\\' + img)
        img_edit.normalize()

    to_compress = [file for file in os.listdir(settings.output_dir) if os.path.splitext(file)[1] in valid_ext]

    for img in to_compress:
        img_compress = Compressor(settings.output_dir + '\\' + img)
        img_compress.compress()

batch_process()