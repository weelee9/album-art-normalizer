# album-art-normalizer

## Features
 - Resizes album art to target dimensions.
 - Pads non 1:1 aspect ratio album art with transparency.
 - Compresses PNGs using quantization with pngquant, and lossless compression with optipng.
 - Lossless compression for JPEGs using jpegoptim.
 
## Usage
 1. Place pngquant, optipng, and jpegoptim executables in the same directory as script.
 2. Direct the input and output directories in settings.py (preferably in the same directory).
 3. Run the script.
 
## To-do
 - Verbose mode.
 - Image upscaling for low resolution album art.
