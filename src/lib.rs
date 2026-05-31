use zed_extension_api::{self as zed, LanguageServerId, Result, Worktree};

struct VapourSynthExtension;

impl zed::Extension for VapourSynthExtension {
    fn new() -> Self {
        Self
    }

    fn language_server_command(
        &mut self,
        language_server_id: &LanguageServerId,
        worktree: &Worktree,
    ) -> Result<zed::Command> {
        match language_server_id.as_ref() {
            "vapoursynth-basedpyright" => basedpyright_command(worktree),
            "vapoursynth-ruff" => ruff_command(worktree),
            _ => Err(format!(
                "unknown language server: {}",
                language_server_id.as_ref()
            )),
        }
    }

    fn language_server_initialization_options(
        &mut self,
        language_server_id: &LanguageServerId,
        worktree: &Worktree,
    ) -> Result<Option<zed::serde_json::Value>> {
        match language_server_id.as_ref() {
            "vapoursynth-basedpyright" => Ok(Some(zed::serde_json::json!({
                "settings": python_settings(worktree)?,
            }))),
            "vapoursynth-ruff" => Ok(Some(zed::serde_json::json!({
                "settings": {
                    "logLevel": "info",
                },
            }))),
            _ => Ok(None),
        }
    }

    fn language_server_workspace_configuration(
        &mut self,
        language_server_id: &LanguageServerId,
        worktree: &Worktree,
    ) -> Result<Option<zed::serde_json::Value>> {
        match language_server_id.as_ref() {
            "vapoursynth-basedpyright" => Ok(Some(python_settings(worktree)?)),
            "vapoursynth-ruff" => Ok(Some(zed::serde_json::json!({}))),
            _ => Ok(None),
        }
    }
}

fn basedpyright_command(worktree: &Worktree) -> Result<zed::Command> {
    let mut env = worktree.shell_env();
    let python = python_path(worktree, &env).ok_or_else(|| {
        "failed to find Python. Set VPY_PYTHON to the full path of python.exe".to_string()
    })?;
    let node = worktree
        .which("node")
        .or_else(|| worktree.which("node.exe"))
        .or_else(|| zed::node_binary_path().ok())
        .ok_or_else(|| "failed to find Node.js for basedpyright".to_string())?;
    let local_app_data = local_app_data(&env)?;
    let server = format!(
        "{}\\Zed\\languages\\basedpyright\\node_modules\\basedpyright\\langserver.index.js",
        local_app_data
    );
    let powershell =
        powershell_path(worktree).ok_or_else(|| "failed to find PowerShell".to_string())?;
    let stub_dir = stub_dir(&env)?;
    prepend_env_path(&mut env, "PYTHONPATH", &stub_dir);
    let stub_file = format!("{stub_dir}\\vapoursynth.pyi");
    let generators = powershell_array(extension_script_paths(
        "generate_vapoursynth_stubs.py",
        &env,
    ));
    let script = format!(
        r#"$ErrorActionPreference = 'Continue'
$python = '{}'
$node = '{}'
$server = '{}'
$generator = @({}) | Where-Object {{ $_ -and (Test-Path -LiteralPath $_) }} | Select-Object -First 1
$stubFile = '{}'
if ($generator) {{
    try {{
        $stubDir = Split-Path -Parent $stubFile
        $helperMarker = Join-Path $stubDir '.helper-stubs'
        $helperVersion = '4:'
        New-Item -ItemType Directory -Path $stubDir -Force | Out-Null
        $force = $env:VPY_STUBS_UPDATE -match '^(1|true|yes)$'
        $helperMarkerText = ''
        if (Test-Path -LiteralPath $helperMarker) {{
            $helperMarkerText = Get-Content -LiteralPath $helperMarker -Raw -ErrorAction SilentlyContinue
        }}
        $helperStubsCurrent = $helperMarkerText -and $helperMarkerText.StartsWith($helperVersion)
        if ($force -or -not (Test-Path -LiteralPath $stubFile) -or -not $helperStubsCurrent) {{
            & $python $generator --output $stubFile 1>$null
            if ($LASTEXITCODE -ne 0) {{
                [Console]::Error.WriteLine('failed to generate VapourSynth stubs')
            }}
        }}
    }} catch {{
        [Console]::Error.WriteLine('failed to generate VapourSynth stubs: ' + $_.Exception.Message)
    }}
}} else {{
    [Console]::Error.WriteLine('failed to find VapourSynth stub generator')
}}
& $node $server --stdio
exit $LASTEXITCODE"#,
        escape_powershell_single_quoted(&python),
        escape_powershell_single_quoted(&node),
        escape_powershell_single_quoted(&server),
        generators,
        escape_powershell_single_quoted(&stub_file),
    );

    Ok(zed::Command {
        command: powershell,
        args: vec!["-NoProfile".into(), "-Command".into(), script],
        env,
    })
}

fn ruff_command(worktree: &Worktree) -> Result<zed::Command> {
    let env = worktree.shell_env();
    let local_app_data = local_app_data(&env)?;
    let powershell = powershell_path(worktree)
        .ok_or_else(|| "failed to find PowerShell for ruff".to_string())?;
    let script = format!(
        "$ruff = Get-ChildItem -LiteralPath '{}\\Zed\\languages\\ruff' -Recurse -Filter ruff.exe -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1; if ($ruff) {{ & $ruff.FullName server }} elseif (Get-Command ruff -ErrorAction SilentlyContinue) {{ & ruff server }} else {{ Write-Error 'failed to find ruff language server' }}",
        escape_powershell_single_quoted(&local_app_data)
    );

    Ok(zed::Command {
        command: powershell,
        args: vec!["-NoProfile".into(), "-Command".into(), script],
        env,
    })
}

fn python_settings(worktree: &Worktree) -> Result<zed::serde_json::Value> {
    let env = worktree.shell_env();
    let python = python_path(worktree, &env).ok_or_else(|| {
        "failed to find Python. Set VPY_PYTHON to the full path of python.exe".to_string()
    })?;
    let extra_paths = python_extra_paths(&python, worktree, &env);
    let analysis = zed::serde_json::json!({
        "autoImportCompletions": true,
        "useLibraryCodeForTypes": true,
        "diagnosticMode": "workspace",
        "extraPaths": extra_paths,
        "diagnosticSeverityOverrides": {
            "reportMissingTypeStubs": "none",
        },
        "reportMissingTypeStubs": "none",
    });

    Ok(zed::serde_json::json!({
        "pythonPath": python,
        "autoImportCompletions": true,
        "useLibraryCodeForTypes": true,
        "diagnosticMode": "workspace",
        "extraPaths": extra_paths,
        "diagnosticSeverityOverrides": {
            "reportMissingTypeStubs": "none",
        },
        "reportMissingTypeStubs": "none",
        "python": {
            "pythonPath": python.clone(),
            "analysis": analysis.clone(),
        },
        "basedpyright": {
            "analysis": analysis,
        },
    }))
}

fn python_extra_paths(python: &str, worktree: &Worktree, env: &zed::EnvVars) -> Vec<String> {
    let Some(root) = parent_dir(python) else {
        return Vec::new();
    };

    let mut paths = Vec::new();

    if let Some(stubs_path) = env_var(env, "VPY_STUBS_PATH") {
        paths.push(stubs_path);
    }

    if let Ok(stubs_path) = stub_dir(env) {
        paths.push(stubs_path);
    }

    paths.extend([
        root.to_string(),
        format!("{root}\\Lib"),
        format!("{root}\\DLLs"),
        format!("{root}\\Lib\\site-packages"),
        format!("{root}\\VapourSynthScripts"),
        format!("{}\\.zed-vapoursynth-stubs", worktree.root_path()),
    ]);

    paths
}

fn python_path(worktree: &Worktree, env: &zed::EnvVars) -> Option<String> {
    env_var(env, "VPY_PYTHON")
        .or_else(|| worktree.which("vpy.exe"))
        .or_else(|| worktree.which("python"))
        .or_else(|| worktree.which("python.exe"))
}

fn local_app_data(env: &zed::EnvVars) -> Result<String> {
    env_var(env, "LOCALAPPDATA").ok_or_else(|| "failed to find LOCALAPPDATA".to_string())
}

fn stub_dir(env: &zed::EnvVars) -> Result<String> {
    Ok(format!("{}\\Zed\\vapoursynth\\stubs", local_app_data(env)?))
}

fn env_var(env: &zed::EnvVars, name: &str) -> Option<String> {
    env.iter().find_map(|(key, value)| {
        (key.eq_ignore_ascii_case(name) && !value.is_empty())
            .then(|| value.trim_matches('"').to_string())
    })
}

fn powershell_path(worktree: &Worktree) -> Option<String> {
    worktree
        .which("pwsh")
        .or_else(|| worktree.which("pwsh.exe"))
        .or_else(|| worktree.which("powershell"))
        .or_else(|| worktree.which("powershell.exe"))
}

fn prepend_env_path(env: &mut zed::EnvVars, name: &str, path: &str) {
    if let Some((_, value)) = env
        .iter_mut()
        .find(|(key, _)| key.eq_ignore_ascii_case(name))
    {
        if value.is_empty() {
            *value = path.to_string();
        } else if !env_path_contains(value, path) {
            *value = format!("{path};{value}");
        }
    } else {
        env.push((name.to_string(), path.to_string()));
    }
}

fn env_path_contains(value: &str, path: &str) -> bool {
    value
        .split(';')
        .any(|entry| entry.trim_matches('"').eq_ignore_ascii_case(path))
}

fn extension_script_paths(filename: &str, env: &zed::EnvVars) -> Vec<String> {
    let mut paths = Vec::new();

    if let Ok(mut path) = std::env::current_dir() {
        path.push("scripts");
        path.push(filename);
        paths.push(path.to_string_lossy().to_string());
    }

    if let Ok(local_app_data) = local_app_data(env) {
        paths.push(format!(
            "{local_app_data}\\Zed\\extensions\\installed\\vapoursynth\\scripts\\{filename}",
        ));
    }

    paths
}

fn powershell_array(values: Vec<String>) -> String {
    values
        .into_iter()
        .map(|value| format!("'{}'", escape_powershell_single_quoted(&value)))
        .collect::<Vec<_>>()
        .join(", ")
}

fn parent_dir(path: &str) -> Option<&str> {
    let backslash = path.rfind('\\');
    let slash = path.rfind('/');
    let index = match (backslash, slash) {
        (Some(backslash), Some(slash)) => backslash.max(slash),
        (Some(index), None) | (None, Some(index)) => index,
        (None, None) => return None,
    };

    Some(&path[..index])
}

fn escape_powershell_single_quoted(value: &str) -> String {
    value.replace('\'', "''")
}

zed::register_extension!(VapourSynthExtension);
