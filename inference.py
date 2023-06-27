import torch
from config import repo_name, model_name, model_basename, max_new_tokens, token_repetition_penalty_max, temperature, top_p, top_k, typical, stop_sequence
from huggingface_hub import snapshot_download
import logging, os, glob
from exllama.model import ExLlama, ExLlamaCache, ExLlamaConfig
from exllama.tokenizer import ExLlamaTokenizer
from exllama.generator import ExLlamaGenerator

class Predictor:
    def setup(self):
        # Model moved to network storage
        model_directory = f"/runpod-volume/{model_name}"
        
        # print the file list and the directory list inside /
        print("Files and directories in /:")
        for item in os.scandir("/"):
            if item.is_file():
                print(f"File: {item.name}")
            elif item.is_dir():
                print(f"Directory: {item.name}")

# print the file list and the directory list inside f"/workspace/{model_name}"
        print(f"Files and directories in /runpod-volume/{model_name}:")
        for item in os.scandir(f"/runpod-volume/{model_name}"):
            if item.is_file():
                print(f"File: {item.name}")
            elif item.is_dir():
                print(f"Directory: {item.name}")
                
        # snapshot_download(repo_id=repo_name, local_dir=model_directory)
        print()
        tokenizer_path = os.path.join(model_directory, "tokenizer.model")
        model_config_path = os.path.join(model_directory, "config.json")
        st_pattern = os.path.join(model_directory, "*.safetensors")
        model_path = glob.glob(st_pattern)[0]
        
        config = ExLlamaConfig(model_config_path)               # create config from config.json
        config.model_path = model_path                          # supply path to model weights file
        
        
        """Load the model into memory to make running multiple predictions efficient"""
        print("Loading tokenizer...")
        
        self.tokenizer = ExLlamaTokenizer(tokenizer_path)            # create tokenizer from tokenizer model file
        
        print("Loading model...")
        
        self.model = ExLlama(config)                                 # create ExLlama instance and load the weights
        
        print("Creating cache...")
        self.cache = ExLlamaCache(self.model)                             # create cache for inference
        
        print("Creating generator...")
        self.generator = ExLlamaGenerator(self.model, self.tokenizer, self.cache)   # create generator
        # Configure generator
        self.generator.disallow_tokens([self.tokenizer.eos_token_id])

        self.generator.settings.token_repetition_penalty_max = token_repetition_penalty_max
        self.generator.settings.temperature = temperature
        self.generator.settings.top_p = top_p
        self.generator.settings.top_k = top_k
        self.generator.settings.typical = typical
        
    def predict(self, prompt):
        
        return self.generate_to_eos(prompt)
    
    def generate_to_eos(self, prompt):
        
        self.generator.end_beam_search()

        ids = self.tokenizer.encode(prompt)
        num_res_tokens = ids.shape[-1]  # Decode from here
        self.generator.gen_begin(ids)

        self.generator.begin_beam_search()
        for i in range(max_new_tokens):
            gen_token = self.generator.beam_search()
            if gen_token.item() == self.tokenizer.eos_token_id:
                self.generator.replace_last_token(self.tokenizer.newline_token_id)
                return text

            num_res_tokens += 1
            text = self.tokenizer.decode(self.generator.sequence_actual[:, -num_res_tokens:][0])
            if text.lower().endswith(stop_sequence.lower()):
                plen = self.tokenizer.encode(stop_sequence).shape[-1]
                self.generator.gen_rewind(plen)
                return text

        return text
