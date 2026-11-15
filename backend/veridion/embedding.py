import os
from functools import lru_cache
from threading import Lock

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL = "Xenova/multilingual-e5-small@761b726dd34fb83930e26aab4e9ac3899aa1fa78:int8"
INDEX = "nfc-window-780-110/v1"
STARTUP_LOCK = Lock()


@lru_cache(maxsize=1)
def load_runtime():
    model_dir = os.getenv("VERIDION_EMBEDDINGS", "/models/e5")
    tokenizer = Tokenizer.from_file(f"{model_dir}/tokenizer.json")
    tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
    tokenizer.enable_truncation(max_length=512)
    options = ort.SessionOptions()
    options.enable_cpu_mem_arena = False
    options.enable_mem_pattern = False
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    network = ort.InferenceSession(
        f"{model_dir}/model.onnx",
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    return tokenizer, network


def embed(texts: list[str], *, query: bool = False) -> list[str]:
    with STARTUP_LOCK:
        tokenizer, network = load_runtime()
    prefix = "query: " if query else "passage: "
    encodings = tokenizer.encode_batch([prefix + text for text in texts])
    mask = np.array([encoding.attention_mask for encoding in encodings], dtype=np.int64)
    inputs = {
        "input_ids": np.array([encoding.ids for encoding in encodings], dtype=np.int64),
        "attention_mask": mask,
        "token_type_ids": np.zeros_like(mask),
    }
    output = network.run(
        None, {key.name: inputs[key.name] for key in network.get_inputs()}
    )[0]
    pooled = (output * mask[:, :, None]).sum(axis=1) / mask.sum(axis=1, keepdims=True)
    vectors = pooled / np.linalg.norm(pooled, axis=1, keepdims=True)
    return [
        "[" + ",".join(f"{element:.8f}" for element in vector) + "]"
        for vector in vectors
    ]
