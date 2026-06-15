import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.handler import pipeline, handler, initialize_pipeline

initialize_pipeline()

import runpod

runpod.serverless.start({"handler": handler})
