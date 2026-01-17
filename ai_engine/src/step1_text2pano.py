#!/usr/bin/env python3
"""
Step 1: Text to Panorama Generation
Generates a 360-degree panorama image from text prompt using HunyuanWorld-1.0
"""

import os
import argparse
import logging
import torch
import boto3
from PIL import Image

# Configure logging for CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# HunyuanWorld imports
from hy3dworld import Text2PanoramaPipelines
from hy3dworld.AngelSlim.gemm_quantization_processor import FluxFp8GeMMProcessor
from hy3dworld.AngelSlim.attention_quantization_processor import FluxFp8AttnProcessor2_0
from hy3dworld.AngelSlim.cache_helper import DeepCacheHelper


class Text2PanoramaGenerator:
    def __init__(self, args):
        self.args = args
        self.height = 960
        self.width = 1920
        
        # Panorama generation parameters
        self.guidance_scale = 30
        self.num_inference_steps = 50
        self.blend_extend = 6
        
        # Model paths
        self.lora_path = "tencent/HunyuanWorld-1"
        self.model_path = "black-forest-labs/FLUX.1-dev"
        
        logger.info("[Step 1] Loading Text2Panorama pipeline...")
        
        # Load pipeline with bfloat16
        self.pipe = Text2PanoramaPipelines.from_pretrained(
            self.model_path,
            torch_dtype=torch.bfloat16
        )
        
        # Load LoRA weights
        self.pipe.load_lora_weights(
            self.lora_path,
            subfolder="HunyuanWorld-PanoDiT-Text",
            weight_name="lora.safetensors",
            torch_dtype=torch.bfloat16
        )
        self.pipe.fuse_lora()
        self.pipe.unload_lora_weights()
        
        # Enable optimizations
        self.pipe.enable_model_cpu_offload()
        self.pipe.enable_vae_tiling()
        
        # Apply FP8 quantization for memory efficiency
        if self.args.fp8_attention:
            logger.info("[Optimization] Enabling FP8 Attention")
            self.pipe.transformer.set_attn_processor(FluxFp8AttnProcessor2_0())
        
        if self.args.fp8_gemm:
            logger.info("[Optimization] Enabling FP8 GeMM")
            FluxFp8GeMMProcessor(self.pipe.transformer)
        
        self.helper = None
        if self.args.cache:
            logger.info("[Optimization] Enabling DeepCache")
            # pipe_modelにtransformerを渡し、no_cache_steps等は__init__で指定
            self.helper = DeepCacheHelper(
                pipe_model=self.pipe.transformer,
                no_cache_steps=list(range(0, 10)) + list(range(10, 40, 3)) + list(range(40, 50)),
                no_cache_block_id={"single": [38]}
            )
            self.helper.start_timestep = 0
            self.helper.enable()
        
        # Default prompts
        self.general_negative_prompt = (
            "human, person, people, messy, "
            "low-quality, blur, noise, low-resolution"
        )
        self.general_positive_prompt = "high-quality, high-resolution, sharp, clear, 8k"
    
    def generate(self, prompt, negative_prompt="", seed=42):
        """Generate panorama from text prompt"""
        # Combine prompts
        full_prompt = f"{prompt}, {self.general_positive_prompt}"
        full_negative = f"{negative_prompt}, {self.general_negative_prompt}"
        logger.info(f"[Step 1] Generating panorama from prompt: {prompt}")
        logger.info(f"[Config] Seed: {seed}, Steps: {self.num_inference_steps}")
        # Set random seed
        generator = torch.Generator(device="cuda").manual_seed(seed)
        # Generate panorama
        pipe_kwargs = dict(
            prompt=full_prompt,
            negative_prompt=full_negative,
            height=self.height,
            width=self.width,
            guidance_scale=self.guidance_scale,
            num_inference_steps=self.num_inference_steps,
            generator=generator,
            blend_extend=self.blend_extend,
        )
        # DeepCache有効時はhelperを渡す
        if self.helper is not None:
            pipe_kwargs["helper"] = self.helper
        output = self.pipe(**pipe_kwargs)
        return output.images[0]


def main():
    parser = argparse.ArgumentParser(description="Step 1: Text to Panorama Generation")
    
    # Required arguments
    parser.add_argument("--prompt", type=str, required=True,
                        help="Text prompt for panorama generation")
    parser.add_argument("--output_dir", type=str, 
                        default="/opt/ml/processing/output",
                        help="Output directory (SageMaker: /opt/ml/processing/output)")
    
    # Optional arguments
    parser.add_argument("--negative_prompt", type=str, default="",
                        help="Negative prompt")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    parser.add_argument("--theme", type=str, default="demo",
                        help="Theme name for organizing outputs (default: demo)")
    
    # S3 output (optional)
    parser.add_argument("--s3_bucket", type=str, default=os.environ.get('S3_OUTPUT_BUCKET', 'team11-data-source'),
                        help="S3 bucket for output (default: team11-data-source)")
    parser.add_argument("--s3_prefix", type=str, default="",
                        help="S3 prefix for output (default: auto-generated from theme)")
    
    # Optimization flags (default: enabled for ml.g5.2xlarge)
    parser.add_argument("--fp8_attention", action='store_true', default=True,
                        help="Enable FP8 attention quantization (default: True)")
    parser.add_argument("--fp8_gemm", action='store_true', default=True,
                        help="Enable FP8 GeMM quantization (default: True)")
    parser.add_argument("--cache", action='store_true', default=True,
                        help="Enable DeepCache acceleration (default: True)")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize generator
    generator = Text2PanoramaGenerator(args)
    
    # Generate panorama
    panorama_image = generator.generate(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        seed=args.seed
    )
    
    # Save output
    output_path = os.path.join(args.output_dir, "panorama.png")
    panorama_image.save(output_path)
    
    logger.info(f"[Step 1 Complete] Panorama saved to: {output_path}")
    logger.info(f"[Output] Size: {panorama_image.size}")
    
    # Upload to S3 if specified
    if args.s3_bucket:
        s3_client = boto3.client('s3', region_name='ap-northeast-1')
        
        # Auto-generate prefix from theme if not specified
        s3_prefix = args.s3_prefix if args.s3_prefix else f"3dworlds/{args.theme}/"
        s3_key = f"{s3_prefix}panorama.png"
        
        logger.info(f"[S3 Upload] Uploading to s3://{args.s3_bucket}/{s3_key}")
        s3_client.upload_file(output_path, args.s3_bucket, s3_key)
        logger.info(f"[S3 Upload] Complete: s3://{args.s3_bucket}/{s3_key}")
    
    # Memory cleanup
    del generator
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
