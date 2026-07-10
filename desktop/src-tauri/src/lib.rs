use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;
use std::sync::Mutex;
use tauri::State;

#[derive(Default)]
struct WorkflowSession(Mutex<Value>);

fn merge_payload(base: &mut Value, update: &Value) {
    match (base, update) {
        (Value::Object(base_map), Value::Object(update_map)) => {
            for (key, value) in update_map {
                merge_payload(base_map.entry(key.clone()).or_insert(Value::Null), value);
            }
        }
        (base, update) => *base = update.clone(),
    }
}

#[tauri::command]
fn run_python_task(task: String, payload: Value, session: State<'_, WorkflowSession>) -> Result<Value, String> {
    let command = match task.as_str() {
        "import" => "task.import",
        "clean" => "task.clean",
        "lda" => "task.lda",
        "stm" => "task.stm",
        "compare" => "task.compare",
        "export" => "task.export",
        _ => return Err(format!("未知任务：{}", task)),
    };

    let mut session_payload = {
        let saved = session.0.lock().map_err(|_| "工作流会话已锁定".to_string())?;
        if task == "import" { Value::Object(Default::default()) } else { saved.clone() }
    };
    merge_payload(&mut session_payload, &payload);

    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let project_root = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .ok_or_else(|| "无法定位项目根目录".to_string())?;
    let venv_python = project_root.join(".venv").join("Scripts").join("python.exe");
    let python = if venv_python.exists() {
        venv_python.to_string_lossy().to_string()
    } else {
        std::env::var("TOPIC_ANALYZER_PYTHON").unwrap_or_else(|_| "python".to_string())
    };
    let output = Command::new(python)
        .current_dir(project_root)
        .arg("-m")
        .arg("backend.bridge")
        .arg(command)
        .arg(session_payload.to_string())
        .output()
        .map_err(|err| format!("启动 Python bridge 失败：{}", err))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let json_line = stdout.lines().rev().find(|line| !line.trim().is_empty());
    let Some(json_line) = json_line else {
        return Err(format!("Python bridge 未返回结果：{}", stderr.trim()));
    };

    let response: Value = serde_json::from_str(json_line.trim()).map_err(|err| {
        format!("解析 Python bridge 返回失败：{}；stderr：{}", err, stderr.trim())
    })?;

    if response.get("ok").and_then(Value::as_bool) == Some(true) {
        let mut saved = session.0.lock().map_err(|_| "工作流会话已锁定".to_string())?;
        *saved = session_payload;
    }
    Ok(response)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(WorkflowSession::default())
        .invoke_handler(tauri::generate_handler![run_python_task])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
