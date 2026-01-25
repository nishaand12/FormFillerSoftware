"""Separate process handler for llama.cpp inference."""

from __future__ import annotations

import logging
import multiprocessing as mp
import queue
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from runtime.hardware_profile import LlamaRuntimeConfig


@dataclass
class LoadRequest:
    model_type: str
    model_path: str
    runtime_cfg: LlamaRuntimeConfig


@dataclass
class ProcessRequest:
    model_type: str
    prompt: str
    max_tokens: int
    temperature: float
    stop_sequences: Optional[list]


def _resolve_model_path(model_type: str) -> str:
    from app_paths import get_writable_path
    from pathlib import Path
    import sys

    try:
        if model_type == "qwen3-4b":
            return str(get_writable_path("models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"))
        if model_type == "qwen3-1.7b":
            return str(get_writable_path("models/Qwen3-1.7B-Q8_0.gguf"))
        return str(get_writable_path("models/mistral-7b-instruct-v0.1.Q4_K_M.gguf"))
    except ImportError:
        import os
        from pathlib import Path

        if sys.platform == "darwin":
            base_dir = Path.home() / "Library" / "Application Support" / "PhysioClinicAssistant" / "models"
        elif sys.platform == "win32":
            base_dir = Path(os.getenv('APPDATA', Path.home())) / "PhysioClinicAssistant" / "models"
        else:
            base_dir = Path.home() / ".local" / "share" / "PhysioClinicAssistant" / "models"

        if model_type == "qwen3-4b":
            return str(base_dir / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")
        if model_type == "qwen3-1.7b":
            return str(base_dir / "Qwen3-1.7B-Q8_0.gguf")
        return str(base_dir / "mistral-7b-instruct-v0.1.Q4_K_M.gguf")


def _worker_main(request_queue: mp.Queue, response_queue: mp.Queue) -> None:
    logging.basicConfig(level=logging.INFO, format="[worker] %(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("inference-worker")

    from llama_cpp import Llama

    current_model: Optional[Llama] = None
    current_model_type: Optional[str] = None
    current_runtime: Optional[LlamaRuntimeConfig] = None

    def _load_model(req: LoadRequest) -> Dict[str, Any]:
        nonlocal current_model, current_model_type, current_runtime

        if current_model is not None and current_model_type == req.model_type:
            if current_runtime and current_runtime.n_ctx == req.runtime_cfg.n_ctx:
                return {"success": True}
            try:
                del current_model
            except Exception:
                pass
            current_model = None

        try:
            current_model = Llama(
                model_path=req.model_path,
                n_ctx=req.runtime_cfg.n_ctx,
                n_threads=req.runtime_cfg.n_threads,
                n_gpu_layers=req.runtime_cfg.n_gpu_layers,
                verbose=False,
            )
            current_model_type = req.model_type
            current_runtime = req.runtime_cfg
            logger.info(
                "Loaded %s model (n_ctx=%s, n_threads=%s, n_gpu_layers=%s)",
                req.model_type,
                req.runtime_cfg.n_ctx,
                req.runtime_cfg.n_threads,
                req.runtime_cfg.n_gpu_layers,
            )
            return {"success": True}
        except Exception as exc:
            logger.exception("Failed to load model %s", req.model_type)
            current_model = None
            current_model_type = None
            current_runtime = None
            return {"success": False, "error": str(exc)}

    def _process(req: ProcessRequest) -> Dict[str, Any]:
        nonlocal current_model, current_model_type

        if current_model is None or current_model_type != req.model_type:
            load_result = _load_model(
                LoadRequest(
                    model_type=req.model_type,
                    model_path=_resolve_model_path(req.model_type),
                    runtime_cfg=current_runtime or LlamaRuntimeConfig(n_ctx=2048, n_threads=1, n_gpu_layers=0, max_tokens=req.max_tokens),
                )
            )
            if not load_result.get("success"):
                return load_result

        try:
            response = current_model(
                req.prompt,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                stop=req.stop_sequences,
            )
            text = response["choices"][0]["text"].strip() if response.get("choices") else ""
            return {"success": True, "response": response, "text": text}
        except Exception as exc:
            logger.exception("Inference failed for model %s", req.model_type)
            return {"success": False, "error": str(exc)}

    while True:
        message = request_queue.get()
        command = message.get("command")
        identifier = message.get("id")

        if command == "shutdown":
            break

        if command == "load":
            load_req: LoadRequest = message["payload"]
            result = _load_model(load_req)
            response_queue.put({"id": identifier, **result})
            continue

        if command == "process":
            proc_req: ProcessRequest = message["payload"]
            result = _process(proc_req)
            response_queue.put({"id": identifier, **result})
            continue

        if command == "reload":
            if current_model is not None:
                try:
                    del current_model
                except Exception:
                    pass
            current_model = None
            current_model_type = None
            current_runtime = None
            response_queue.put({"id": identifier, "success": True})
            continue

        if command == "health_check":
            ok = current_model is not None
            response_queue.put({"id": identifier, "success": ok})


class InferenceWorkerController:
    def __init__(self, logger: logging.Logger, timeout: int = 240):
        self._logger = logger
        self._timeout = timeout
        self._ctx = mp.get_context("spawn")
        self._request_queue: mp.Queue = self._ctx.Queue()
        self._response_queue: mp.Queue = self._ctx.Queue()
        self._process: Optional[mp.Process] = None
        self._start_worker()

    def _start_worker(self) -> None:
        if self._process and self._process.is_alive():
            return
        self._process = self._ctx.Process(target=_worker_main, args=(self._request_queue, self._response_queue))
        self._process.daemon = True
        self._process.start()
        self._logger.info("Inference worker started with PID %s", self._process.pid)

    def _await_response(self, identifier: str) -> Dict[str, Any]:
        start = time.time()
        while True:
            remaining = self._timeout - (time.time() - start)
            if remaining <= 0:
                raise TimeoutError("Inference worker timed out")
            try:
                response = self._response_queue.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError("Inference worker timed out waiting for response")

            if response.get("id") == identifier:
                return response

    def ensure_model(self, model_type: str, model_path: str, runtime_cfg: LlamaRuntimeConfig) -> Dict[str, Any]:
        identifier = uuid.uuid4().hex
        self._request_queue.put({
            "id": identifier,
            "command": "load",
            "payload": LoadRequest(model_type=model_type, model_path=model_path, runtime_cfg=runtime_cfg),
        })
        return self._await_response(identifier)

    def process_prompt(self, req: ProcessRequest) -> Dict[str, Any]:
        identifier = uuid.uuid4().hex
        self._request_queue.put({
            "id": identifier,
            "command": "process",
            "payload": req,
        })
        return self._await_response(identifier)

    def reload_model(self) -> None:
        identifier = uuid.uuid4().hex
        self._request_queue.put({"id": identifier, "command": "reload"})
        self._await_response(identifier)

    def health_check(self) -> bool:
        identifier = uuid.uuid4().hex
        self._request_queue.put({"id": identifier, "command": "health_check"})
        response = self._await_response(identifier)
        return bool(response.get("success"))

    def shutdown(self) -> None:
        if not self._process:
            return
        try:
            self._request_queue.put({"command": "shutdown", "id": uuid.uuid4().hex})
        except Exception:
            pass
        self._process.join(timeout=5)
        if self._process.is_alive():
            self._process.terminate()
        self._process = None


