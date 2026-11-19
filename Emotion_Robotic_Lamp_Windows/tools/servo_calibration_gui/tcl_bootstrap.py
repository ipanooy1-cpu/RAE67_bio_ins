"""Work around incomplete Tcl discovery in some Windows Python installs."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


_TCL_DLL = None


def prepare_tcl_runtime() -> bool:
    """Initialize Tcl's library path before tkinter imports `_tkinter`.

    Returns True when the Windows bootstrap ran successfully. On normal
    installations and non-Windows platforms it safely returns False and lets
    tkinter perform its standard initialization.
    """

    global _TCL_DLL
    if os.name != "nt" or "_tkinter" in sys.modules:
        return False
    python_dir = Path(sys.executable).resolve().parent
    dll_path = python_dir / "DLLs" / "tcl86t.dll"
    library_path = python_dir / "tcl" / "tcl8.6"
    init_path = library_path / "init.tcl"
    if not dll_path.is_file() or not init_path.is_file():
        return False

    try:
        dll = ctypes.CDLL(str(dll_path))
        dll.Tcl_FindExecutable.argtypes = [ctypes.c_char_p]
        dll.Tcl_FindExecutable(str(sys.executable).replace("\\", "/").encode("utf-8"))
        dll.Tcl_CreateInterp.restype = ctypes.c_void_p
        interpreter = dll.Tcl_CreateInterp()
        if not interpreter:
            return False
        dll.Tcl_SetVar.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        dll.Tcl_SetVar.restype = ctypes.c_char_p
        dll.Tcl_SetVar(
            interpreter,
            b"tcl_library",
            library_path.as_posix().encode("utf-8"),
            1,
        )
        dll.Tcl_Init.argtypes = [ctypes.c_void_p]
        dll.Tcl_Init.restype = ctypes.c_int
        initialized = dll.Tcl_Init(interpreter) == 0
        dll.Tcl_DeleteInterp.argtypes = [ctypes.c_void_p]
        dll.Tcl_DeleteInterp(interpreter)
        if initialized:
            _TCL_DLL = dll
        return initialized
    except (AttributeError, OSError):
        return False

