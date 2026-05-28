from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


SandboxBackend = Literal["auto", "local", "e2b"]

REMOTE_WORKSPACE = "/home/user/axiom_workspace"


@dataclass(frozen=True)
class SandboxRunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    backend: str = "local"
    sandbox_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class AnalystSandbox:
    def __init__(self, backend: SandboxBackend = "auto") -> None:
        self.backend = backend
        self._e2b_sandbox = None
        self._e2b_unavailable_reason: str | None = None

    @property
    def active_backend(self) -> str:
        if self.backend == "auto":
            return "e2b" if self._can_use_e2b() else "local"
        return self.backend

    def run_attempt(self, script_path: Path, workspace: Path, timeout: int = 60) -> SandboxRunResult:
        if self.active_backend == "e2b":
            return self._run_e2b_attempt(script_path, workspace, timeout)
        return self._run_local_attempt(script_path, workspace, timeout)

    def close(self) -> None:
        if self._e2b_sandbox is None:
            return
        try:
            self._e2b_sandbox.kill()
        except Exception:
            pass
        finally:
            self._e2b_sandbox = None

    def _can_use_e2b(self) -> bool:
        if not os.getenv("E2B_API_KEY"):
            self._e2b_unavailable_reason = "E2B_API_KEY is not set."
            return False
        _enable_system_cert_store()
        try:
            import e2b  # noqa: F401
        except ImportError:
            self._e2b_unavailable_reason = "The e2b package is not installed."
            return False
        return True

    def _run_local_attempt(self, script_path: Path, workspace: Path, timeout: int) -> SandboxRunResult:
        env = os.environ.copy()
        env["PYTHONNOUSERSITE"] = "1"
        try:
            run = subprocess.run(
                [sys.executable, script_path.name],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                shell=False,
            )
            return SandboxRunResult(
                returncode=run.returncode,
                stdout=run.stdout,
                stderr=run.stderr,
                backend="local",
                metadata=_local_metadata(self._e2b_unavailable_reason),
            )
        except subprocess.TimeoutExpired as error:
            return SandboxRunResult(
                returncode=124,
                stdout=error.stdout or "",
                stderr=error.stderr or "Analyst attempt timed out.",
                backend="local",
                metadata=_local_metadata(self._e2b_unavailable_reason),
            )

    def _run_e2b_attempt(self, script_path: Path, workspace: Path, timeout: int) -> SandboxRunResult:
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        try:
            sandbox = self._get_e2b_sandbox(workspace)
            sandbox.files.write(f"{REMOTE_WORKSPACE}/{script_path.name}", script_path.read_text(encoding="utf-8"))
            command = sandbox.commands.run(
                f"python {script_path.name}",
                cwd=REMOTE_WORKSPACE,
                timeout=timeout,
                envs={"PYTHONNOUSERSITE": "1"},
                on_stdout=stdout_chunks.append,
                on_stderr=stderr_chunks.append,
            )
            self._mirror_remote_result(sandbox, workspace)
            return SandboxRunResult(
                returncode=int(getattr(command, "exit_code", 0) or 0),
                stdout="".join(stdout_chunks) or str(getattr(command, "stdout", "") or ""),
                stderr="".join(stderr_chunks) or str(getattr(command, "stderr", "") or ""),
                backend="e2b",
                sandbox_id=_sandbox_id(sandbox),
                metadata={"remote_workspace": REMOTE_WORKSPACE},
            )
        except Exception as error:
            if self._e2b_sandbox is None and self.backend == "e2b":
                raise RuntimeError(f"E2B sandbox could not be started: {error}") from error
            returncode = int(getattr(error, "exit_code", 1) or 1)
            stdout = "".join(stdout_chunks) or _text_from_error_attr(error, "stdout")
            stderr = "".join(stderr_chunks) or _text_from_error_attr(error, "stderr") or str(error)
            if self._e2b_sandbox is not None:
                try:
                    self._mirror_remote_result(self._e2b_sandbox, workspace)
                except Exception:
                    pass
            return SandboxRunResult(
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                backend="e2b",
                sandbox_id=_sandbox_id(self._e2b_sandbox),
                metadata={"remote_workspace": REMOTE_WORKSPACE},
            )

    def _get_e2b_sandbox(self, workspace: Path):
        if self._e2b_sandbox is not None:
            return self._e2b_sandbox
        if not self._can_use_e2b():
            raise RuntimeError(self._e2b_unavailable_reason or "E2B is unavailable.")

        _enable_system_cert_store()
        from e2b import Sandbox

        timeout = int(os.getenv("AXIOM_E2B_TIMEOUT", "300"))
        template = os.getenv("AXIOM_E2B_TEMPLATE") or None
        allow_internet = _env_flag("AXIOM_E2B_ALLOW_INTERNET", default=False)
        self._e2b_sandbox = Sandbox.create(
            template=template,
            timeout=timeout,
            allow_internet_access=allow_internet,
            metadata={"app": "project-axiom", "component": "analyst"},
        )
        try:
            self._e2b_sandbox.files.make_dir(REMOTE_WORKSPACE)
        except Exception:
            pass
        self._upload_workspace_inputs(self._e2b_sandbox, workspace)
        return self._e2b_sandbox

    def _upload_workspace_inputs(self, sandbox, workspace: Path) -> None:
        for filename in ("analysis_input.csv", "manifesto.json", "analysis_plan.json"):
            local_path = workspace / filename
            if local_path.exists():
                sandbox.files.write(f"{REMOTE_WORKSPACE}/{filename}", local_path.read_text(encoding="utf-8"))

    def _mirror_remote_result(self, sandbox, workspace: Path) -> None:
        try:
            result = sandbox.files.read(f"{REMOTE_WORKSPACE}/result.json")
        except Exception:
            return
        (workspace / "result.json").write_text(result, encoding="utf-8")


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _enable_system_cert_store() -> None:
    if not _env_flag("AXIOM_USE_SYSTEM_CERTS", default=True):
        return
    try:
        import truststore
    except ImportError:
        return
    try:
        truststore.inject_into_ssl()
    except Exception:
        pass


def _sandbox_id(sandbox) -> str | None:
    if sandbox is None:
        return None
    return str(getattr(sandbox, "sandbox_id", None) or getattr(sandbox, "id", None) or "") or None


def _text_from_error_attr(error: Exception, name: str) -> str:
    value = getattr(error, name, "")
    if isinstance(value, list):
        return "".join(str(item) for item in value)
    return str(value or "")


def _local_metadata(e2b_unavailable_reason: str | None) -> dict[str, str]:
    if not e2b_unavailable_reason:
        return {}
    return {"e2b_unavailable_reason": e2b_unavailable_reason}
