import os, argparse, requests, json, time, subprocess
from randagent import generate_useragent
from PIL import Image
from io import BytesIO
from pathlib import Path

SHRINK_URL = 'https://tinypng.com/web/shrink'
HEADERS = {
    'user-agent': 'Mozilla/5.0',
    'content-type': 'image/png'
}

class Normalizer:
    def __init__(self):
        self.verbose = True
        self.name = None
        self.output = None
        self.ofiles = []
        self.del_original = True
        self.img = None
        self.png_max = 5120
        self.min_res = 1000
        self.max_res = 2000
        self.jpeg_quality = 85
        self.pad_tolerance = 5
        self.pad_tp_thres = 100

    def log(self, text):
        if self.verbose:
            print(text)

    def batch_normalize(self, files):
        for index, file in enumerate(files):
            self.log(f"({index+1}/{len(files)}) Normalizing {os.path.basename(file)} ...")
            self.normalize(file)

    def normalize(self, file):
        self.img = Image.open(file)
        self.name = os.path.splitext(os.path.basename(file))[0]
        width, height = self.img.size

        self.log(f"  {width}x{height}")

        if max(width, height) > self.max_res:
            self.resize()

        if width != height:
            self.pad()

        self.save()

        if self.del_original: os.remove(file)

    def resize(self):
        self.log("  Resizing image...")
        self.img.thumbnail((self.max_res, self.max_res), Image.Resampling.LANCZOS)

    def pad(self):
        width, height = self.img.size
        diff = abs(width-height)

        if diff <= self.pad_tolerance:
            self.log(f"  Difference of {diff} is under tolerance of {self.pad_tolerance}. Skipping...")
        elif diff > self.pad_tp_thres:
            self.adaptive_resize()
            self.pad_with_colour('tp')
        else:
            self.pad_with_colour('w')

    def pad_with_colour(self, colour):
        width, height = self.img.size
        dim = max(width, height)

        if colour == 'w':
            self.log("  Padding image with white...")
            img_pad = Image.new('RGB', (dim, dim), (255, 255, 255))
            if self.img.mode != 'RGB': self.img = self.img.convert('RGB')
        elif colour == 'tp':
            self.log("  Padding image with transparency...")
            img_pad = Image.new('RGBA', (dim, dim), (0, 0, 0, 0))
            if self.img.mode != 'RGBA': self.img = self.img.convert('RGBA')
        
        if width > height:
            img_pad.paste(self.img, (0, (width-height) // 2))
        else:
            img_pad.paste(self.img, ((height-width) // 2, 0))

        self.img = img_pad
    
    def adaptive_resize(self):
        temp_img = self.img.copy()
        target = max(self.img.size)
        step = 50

        while True:
            temp_store = BytesIO()
            temp_img.save(temp_store, 'png', optimize=True)
            temp_size = temp_store.tell() // (1<<10)

            if temp_size <= self.png_max or target-step < self.min_res:
                temp_img.close()
                self.img.thumbnail((target, target), Image.Resampling.LANCZOS)
                return
            
            self.log("  Adaptively resizing image...")

            target -= step
            temp_img = self.img.copy()
            temp_img.thumbnail((target, target), Image.Resampling.LANCZOS)

    def save(self):
        if self.has_transparency():
            self.save_png()
        else:
            self.save_jpeg()

    def has_transparency(self):
        if self.img.mode == 'RGBA' and self.img.getextrema()[3][0] < 255:
            return True

        if 'transparency' in self.img.info:
            tp = self.img.info['transparency']

            for _, index in self.img.getcolors():
                if index == tp: return True

        return False

    def save_png(self):
        self.log("  Saving as PNG...")

        ofile = f"{self.output}/{self.name}.png"
        self.ofiles.append(ofile)
        self.img.save(ofile, optimize=True)

    def save_jpeg(self):
        self.log("  Saving as JPEG...")

        if (self.img.mode != 'RGB'):
            self.img = self.img.convert('RGB')

        ofile = f"{self.output}/{self.name}.jpg"
        self.ofiles.append(ofile)

        try:
            self.img.save(ofile, optimize=True, quality='keep')
        except ValueError:
            self.img.save(ofile, optimize=True, quality=self.jpeg_quality)

class Compressor:
    def __init__(self):
        self.verbose = True
        self.path = None
        self.raw_data = None
        self.output = None
        self.threshold = 0

    def log(self, text):
        if (self.verbose):
            print(text)

    def batch_compress(self, files):
        for index, file in enumerate(files):
            self.log(f"({index+1}/{len(files)}) Compressing {os.path.basename(file)} ...")
            self.compress(file)

    def compress(self, file):
        self.path = file
        ext = os.path.splitext(self.path)[1]

        if ext == '.jpeg' or ext == '.jpg':
            self.jpegoptim()
            return

        # Left with PNGs here
        if os.path.getsize(self.path) // (1<<10) > self.threshold:
            self.tinypng()
        else:
            print(f"  File size under {self.threshold}KB threshold. Skipping file...")

    def tinypng(self):
        if not self.raw_data:
            raw_data = open(self.path, 'rb').read()

        self.log("  Posting request to Tinypng...")

        HEADERS['user-agent'] = generate_useragent()

        response = requests.post(
            SHRINK_URL,
            headers = HEADERS,
            data=raw_data
        )

        dct = json.loads(response.text)

        if 'error' in dct:
            self.log("  Tinypng did not respond, retrying...")
            time.sleep(3)
            return self.tinypng()

        output = dct['output']
        self.tinypng_save(output['url'])

    def tinypng_save(self, url):
        raw_data = requests.get(
            url,
            headers={'user-agent': generate_useragent()}
        ).content

        self.log("  Saving file from Tinypng...")

        fname = os.path.basename(self.path)
        fpath = os.path.join(self.output, fname)

        os.remove(fpath)

        with open(fpath, 'wb+') as png:
            png.write(raw_data)

    def jpegoptim(self):
        self.log("  Compressing with jpegoptim...")
        subprocess.run(['jpegoptim.exe', '--quiet', '--strip-all', self.path])

def initParser():
    parser = argparse.ArgumentParser()
    # Must be done to add required augments at the front
    parser._action_groups.pop()

    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-p', '--path', type=str, help="Path to PNG/JPG file or directory of PNGs/JPGs.", required=True)
    optional.add_argument('-o', '--output', type=str, default='_output', help="Output folder for compressed images. Defaults to '_output' folder in script directory.")

    return parser
    
def preprocess(path):
    ext = ['.png', '.jpg', '.jpeg']

    if not os.path.exists(path):
        print(f"{path} does not exist!")
        return None
    
    if os.path.isdir(path):
        files = [file for file in Path(path).rglob('*') if os.path.splitext(file)[1] in ext]
        return files

    if os.path.splitext(path)[1] in ext:
        return [path]
    else:
        print("Unsupported file format!")
        return None

def processArgs(args):
    if args.output == '_output' and not os.path.exists(args.output):
        os.mkdir(args.output)
    elif not os.path.isdir(args.output):
        print(f"{args.output} is not a valid output directory!")  
        exit(0)

    output_dir = Path(args.output).rglob('*')

    if output_dir:
        while True:
            ipt = input("Output directory is not empty. Delete all files in output directory? (Y/N) ")

            if ipt.lower() == 'y':
                print("Deleting files...")
                for file in output_dir:
                    os.remove(file)
                
                break
            elif ipt.lower() == 'n':
                break
            else:
                print("Invalid input. Please try again.")

    return args

def begin(args):
    files = preprocess(args.path)

    if not files:
        exit(0)

    nml = Normalizer()
    nml.output = args.output
    nml.batch_normalize(files)

    cmpr = Compressor()
    cmpr.output = args.output
    cmpr.batch_compress(nml.ofiles)

if __name__ == '__main__':
    parser = initParser()
    args = processArgs(parser.parse_args())
    begin(args)