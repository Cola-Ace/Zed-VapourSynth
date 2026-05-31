# Zed-VapourSynth

[English](README.md)

用于 Zed 的 VapourSynth 语言支持扩展。该扩展会将 `.vpy` 文件注册为独立的 `VapourSynth` 语言，并使用 Python Tree-sitter 语法进行高亮。

## 功能

- 通过 Python grammar 为 `.vpy` 文件提供语法高亮。
- 使用独立的 `vapoursynth-basedpyright` 和 `vapoursynth-ruff` language server id，避免与 Zed 内置 Python language server 冲突。
- 基于当前 VapourSynth Python 环境生成带插件信息的 `vapoursynth.pyi`。
- 为 `VapourSynthScripts` 中的辅助模块生成轻量 `.pyi`。
- 提供内置的 `vspreview current vpy` 任务，用于从 Zed 预览当前脚本。

## 注意事项

如果你之前将 `.vpy` 直接映射到了内置 Python，需要先移除该配置，否则本扩展无法接管 `.vpy` 文件：

```json
{
  "file_types": {
    "Python": ["vpy"]
  }
}
```

## Python 环境

`vapoursynth-basedpyright` 会优先使用 `VPY_PYTHON`，然后依次回退到 `vpy.exe`、`python` 和 `python.exe`。

建议将 `VPY_PYTHON` 设置为完整的 VapourSynth Python 解释器路径：

```powershell
[Environment]::SetEnvironmentVariable("VPY_PYTHON", "D:\Path\To\python.exe", "User")
```

修改环境变量后需要重启 Zed。

## VapourSynth Stubs

`vapoursynth-basedpyright` 第一次启动时，会使用同一个 Python 解释器生成插件感知的 stub 文件：

```text
%LOCALAPPDATA%\Zed\vapoursynth\stubs\vapoursynth.pyi
```

该目录会被加入 basedpyright 的 `extraPaths`，并被前置到 language server 的 `PYTHONPATH`，因此补全可以包含 `core.plugins()` 暴露的滤镜。

扩展还会为 `VapourSynthScripts` 中的模块生成轻量 stub，因为 `mvsfunc` 等常见辅助模块通常只有 `.py`，没有对应的 `.pyi`。

安装或更新 VapourSynth 插件后，可以设置 `VPY_STUBS_UPDATE=1` 并重启一次 Zed 来重新生成 stub。也可以设置 `VPY_STUBS_PATH` 指向包含自定义 `vapoursynth.pyi` 的目录，该目录会优先于自动生成的 stub 目录被搜索。

## 运行 vspreview

内置任务会使用相同的 `VPY_PYTHON` 查找逻辑运行 `python -m vspreview "$ZED_FILE"`。它还会在启动新预览前关闭上一次由该任务启动的 `vspreview` 实例。进程会保持附着在 Zed 任务终端中，因此启动错误会留在终端里，而不是在短暂弹窗中消失。

如果想绑定到 `Ctrl+F5`，可以将 `examples/keymap.json` 的内容加入 Zed 用户 keymap。Windows 上通常位于：

```text
%APPDATA%\Zed\keymap.json
```

`keymap.json` 填写示例：

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

## 开发

构建扩展：

```powershell
cargo build --target wasm32-wasip2 --release
```

然后将 release 产物复制为 `extension.wasm`：

```powershell
Copy-Item target\wasm32-wasip2\release\zed_vapoursynth.wasm extension.wasm
```

## 致谢

本项目 `scripts/` 中的 VapourSynth stub 生成部分参照了 [SaltyChiang/VapourSynth-Plugins-Stub-Generator 的 R57Classic 分支](https://github.com/SaltyChiang/VapourSynth-Plugins-Stub-Generator/tree/R57Classic) 进行编写。

相关 stub 材料采用 MIT 许可证；随附声明见 `scripts/LICENSE.vsstubs`。
