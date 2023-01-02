import shutil, os, argparse, requests, json, time, subprocess
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
        self.img = None
        self.png_max = 5120
        self.min_res = 1000
        self.max_res = 2000
        self.pad_tolerance = 30

    def log(self, text):
        if (self.verbose):
            print(text)

    def batch_normalize(self, files):
        for file in files:
            self.log(f"Normalizing {os.path.basename(file)} ...")
            self.name = os.path.splitext(os.path.basename(file))[0]
            self.normalize(file)

    def normalize(self, path):
        self.img = Image.open(path)
        width, height = self.img.size
        ext = os.path.splitext(path)[1]

        pad = abs(width-height) > self.pad_tolerance

        if pad:
            self.adaptive_resize()
            self.pad()
            self.save_png()
        elif width > self.max_res:
            self.resize()
            self.save_jpeg()
        elif ext == '.png':
            self.img = self.img.convert('RGB')
            self.save_jpeg(q=85)
        else:
            self.img.close()
            shutil.move(path, self.output)
            self.ofiles.append(os.path.join(self.output, os.path.basename(path)))
            return

        self.img.close()

    def resize(self):
        self.log("  Resizing image...")
        self.img.thumbnail((self.max_res, self.max_res), Image.Resampling.LANCZOS)
    
    def adaptive_resize(self):
        self.log("  Adaptively resizing image...")
        temp_img = self.img.copy()
        target = self.max_res
        width, height = temp_img.size

        if max(width, height) > target:
            temp_img.thumbnail((target, target), Image.Resampling.LANCZOS)
        else:
            target = max(width, height)

        while True:
            temp_store = BytesIO()
            temp_img.save(temp_store, 'png', optimize=True)
            temp_size = temp_store.tell() // (1<<10)

            if (temp_size <= self.png_max or target < self.min_res):
                temp_img.close()
                self.img.thumbnail((target, target), Image.Resampling.LANCZOS)
                return

            target -= 50
            temp_img = self.img.copy()
            temp_img.thumbnail((target, target), Image.Resampling.LANCZOS)

    def pad(self):
        self.log("  Padding image...")

        width, height = self.img.size
        dim = max(width, height)

        img_pad = Image.new('RGBA', (dim, dim), (0, 0, 0, 0))
        
        if (width > height):
            img_pad.paste(self.img, (0, (width - height) // 2))
        else:
            img_pad.paste(self.img, ((height - width) // 2), 0)

        self.img = img_pad

    def save_png(self):
        ofile = f"{self.output}/{self.name}.png"
        self.ofiles.append(ofile)
        self.img.save(ofile, optimize = True)

    def save_jpeg(self, q='keep'):
        ofile = f"{self.output}/{self.name}.jpg"
        self.ofiles.append(ofile)
        self.img.save(ofile, optimize = True, quality = q)

class Compressor:
    def __init__(self):
        self.verbose = True
        # self.mode = 'tinypng'
        self.path = None
        self.raw_data = None
        self.output = None

    def log(self, text):
        if (self.verbose):
            print(text)

    def batch_compress(self, files):
        for file in files:
            self.path = file
            self.compress()

    def compress(self):
        self.log(f"Compressing {os.path.basename(self.path)} ...")

        ext = os.path.splitext(self.path)[1]

        if (ext == '.png'):
            self.tinypng()
        else:
            self.jpegoptim()

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

# def cmpr_preprocess(path, files):
#     if (isinstance(files[0], Path)):
#         return [os.path.join(path, file.name) for file in files]

#     return [os.path.join(path, os.path.basename(file)) for file in files]

def initParser():
    parser = argparse.ArgumentParser()
    # Must be done to add required augments at the front
    parser._action_groups.pop()

    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-p', '--path', type=str, help="Path to PNG/JPG file or directory of PNGs/JPGs.", required=True)
    optional.add_argument('-o', '--output', type=str, default='_output', help="Output folder for compressed images. Defaults to '_output' folder in script directory.")

    return parser

def processArgs(args):
    if args.output == '_output' and not os.path.exists(args.output):
        os.mkdir(args.output)
    elif not os.path.isdir(args.output):
        print(f"{args.output} is not a valid output directory!")  
        exit(0)

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