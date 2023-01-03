# album-art-normalizer

## Features
 - Resizes album art to target dimensions.
 - Pads non 1:1 aspect ratio album art with transparency.
 - Lossy PNG compression using Tinypng.
 - Lossless JPEG compression using jpegoptim.
 
## Usage
 1. Place jpegoptim executable in the same directory as script.
 2. Run the script. -h or --help for arguments.
 
## To-do
 - Image upscaling for low resolution album art.
 - Add arguments to encompass all available options.

## Changelog
### 2nd January 2023
 - Code overhaul
 - Removed local PNG compression (pngquant and optipng)
 - Added PNG compression using Tinypng without API key (based on [TinyPyng](https://github.com/elmoiv/tinypyng))
 - Added argument parser