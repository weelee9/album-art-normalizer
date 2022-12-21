class Settings:
    def __init__(self):
        self.input_dir = '_input'
        self.output_dir = '_output'
        self.valid_ext = ['.png', '.jpeg', '.jpg']

        # Normalization settings
        self.target_dim = 2000
        self.prequantize_limit = 5120

        # Quantization settings1
        self.speed = 1
        self.floyd = 1