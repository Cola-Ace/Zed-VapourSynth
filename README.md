# Zed-VapourSynth

[简体中文](README.zh-CN.md)

VapourSynth language support for Zed. This extension registers `.vpy` files as a dedicated `VapourSynth` language backed by the Python Tree-sitter grammar.

## Features

- `.vpy` syntax highlighting through the Python grammar.
- Dedicated `vapoursynth-basedpyright` and `vapoursynth-ruff` language server ids, avoiding collisions with Zed's built-in Python servers.
- Plugin-aware `vapoursynth.pyi` generation using the active VapourSynth Python environment.
- Lightweight `.pyi` generation for helper modules found in `VapourSynthScripts`.
- A bundled `vspreview current vpy` task for previewing the current script from Zed.

## Important

Remove any previous setting that maps `.vpy` directly to built-in Python, otherwise this extension will not own `.vpy` files:

```json
{
  "file_types": {
    "Python": ["vpy"]
  }
}
```

## Python Environment

`vapoursynth-basedpyright` uses `VPY_PYTHON` when set, then falls back to `vpy.exe`, `python`, and `python.exe`.

Set `VPY_PYTHON` to the full VapourSynth Python interpreter:

```powershell
[Environment]::SetEnvironmentVariable("VPY_PYTHON", "D:\Path\To\python.exe", "User")
```

Restart Zed after changing environment variables.

## VapourSynth Stubs

`vapoursynth-basedpyright` generates plugin-aware stubs on first start with the same Python interpreter. The generated file is:

```text
%LOCALAPPDATA%\Zed\vapoursynth\stubs\vapoursynth.pyi
```

That directory is added to basedpyright's `extraPaths` and prepended to the language server's `PYTHONPATH`, so completions include filters exposed by `core.plugins()`.

The extension also generates lightweight stubs for modules in `VapourSynthScripts`, because common helper modules such as `mvsfunc` are shipped as `.py` files without matching `.pyi` files.

After installing or updating VapourSynth plugins, set `VPY_STUBS_UPDATE=1` and restart Zed once to regenerate the file. You can also set `VPY_STUBS_PATH` to a directory containing your own `vapoursynth.pyi`; it will be searched before the generated stub directory.

## Run vspreview

The bundled task runs `python -m vspreview "$ZED_FILE"` with the same `VPY_PYTHON` lookup. It also closes the previous task-started `vspreview` instance before launching a new one. The process stays attached to the Zed task terminal, so startup errors remain visible instead of disappearing in a short-lived popup window.

To bind it to `Ctrl+F5`, add the contents of `examples/keymap.json` to your Zed user keymap. On Windows this is usually:

```text
%APPDATA%\Zed\keymap.json
```

Example `keymap.json` entry:

```json
[
  {
    "context": "Workspace",
    "bindings": {
      "ctrl-f5": ["task::Spawn", { "task_name": "vspreview current vpy" }]
    }
  }
]
```

## Development

Build the extension with:

```powershell
cargo build --target wasm32-wasip2 --release
```

Then copy the release artifact to `extension.wasm`:

```powershell
Copy-Item target\wasm32-wasip2\release\zed_vapoursynth.wasm extension.wasm
```

## Credits

The VapourSynth stub generation part in `scripts/` was written with reference to [SaltyChiang/VapourSynth-Plugins-Stub-Generator, R57Classic branch](https://github.com/SaltyChiang/VapourSynth-Plugins-Stub-Generator/tree/R57Classic).

The related stub material is MIT licensed; see `scripts/LICENSE.vsstubs` for the bundled notice.
