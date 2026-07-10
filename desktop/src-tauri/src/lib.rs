use base64::Engine;
use serde::Serialize;
use serde_json::Value;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::Mutex;
use tauri::State;

#[derive(Default)]
struct WorkflowSession(Mutex<Value>);

#[derive(Serialize)]
struct SelectedTextFile {
    path: String,
    content: String,
}

#[tauri::command]
fn select_import_file() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("选择数据表")
        .add_filter("数据表", &["csv", "xlsx", "xls"])
        .pick_file()
        .map(|path| path.to_string_lossy().to_string())
}

#[tauri::command]
fn select_dictionary_file() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("选择自定义词典")
        .add_filter("文本词典", &["txt"])
        .pick_file()
        .map(|path| path.to_string_lossy().to_string())
}

#[tauri::command]
fn select_stopwords_file() -> Result<Option<SelectedTextFile>, String> {
    let Some(path) = rfd::FileDialog::new()
        .set_title("选择停用词文件")
        .add_filter("停用词文本", &["txt"])
        .pick_file()
    else {
        return Ok(None);
    };

    let content =
        fs::read_to_string(&path).map_err(|err| format!("读取停用词文件失败：{}", err))?;
    Ok(Some(SelectedTextFile {
        path: path.to_string_lossy().to_string(),
        content,
    }))
}

#[tauri::command]
fn select_chart_png_path() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("保存当前图表")
        .add_filter("PNG 图片", &["png"])
        .set_file_name("topic_chart.png")
        .save_file()
        .map(|mut path| {
            if path.extension().and_then(|extension| extension.to_str()) != Some("png") {
                path.set_extension("png");
            }
            path.to_string_lossy().to_string()
        })
}

#[tauri::command]
fn save_chart_png(path: String, base64_data: String) -> Result<(), String> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(base64_data)
        .map_err(|err| format!("解析图表图片失败：{}", err))?;
    fs::write(&path, bytes).map_err(|err| format!("保存图表失败：{}", err))
}

#[tauri::command]
fn select_output_directory() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("选择输出目录")
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string())
}

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
fn run_python_task(
    task: String,
    payload: Value,
    session: State<'_, WorkflowSession>,
) -> Result<Value, String> {
    let command = match task.as_str() {
        "import" => "task.import",
        "clean" => "task.clean",
        "lda" => "task.lda",
        "lda-vis" => "lda.open_pyldavis",
        "stm" => "task.stm",
        "stm-check" => "stm.check_r",
        "compare" => "task.compare",
        "export" => "task.export",
        _ => return Err(format!("未知任务：{}", task)),
    };

    let mut session_payload = {
        let saved = session
            .0
            .lock()
            .map_err(|_| "工作流会话已锁定".to_string())?;
        if task == "import" {
            Value::Object(Default::default())
        } else {
            saved.clone()
        }
    };
    merge_payload(&mut session_payload, &payload);

    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let project_root = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .ok_or_else(|| "无法定位项目根目录".to_string())?;
    let venv_python = project_root
        .join(".venv")
        .join("Scripts")
        .join("python.exe");
    let python = if venv_python.exists() {
        venv_python.to_string_lossy().to_string()
    } else {
        std::env::var("TOPIC_ANALYZER_PYTHON").unwrap_or_else(|_| "python".to_string())
    };
    let mut python_command = Command::new(python);
    python_command
        .current_dir(project_root)
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8")
        .env_remove("LC_ALL")
        .env_remove("LC_CTYPE")
        .env_remove("LANG")
        .arg("-m")
        .arg("backend.bridge")
        .arg(command)
        .arg(session_payload.to_string());
    let output = python_command
        .output()
        .map_err(|err| format!("启动 Python bridge 失败：{}", err))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let json_line = stdout.lines().rev().find(|line| !line.trim().is_empty());
    let Some(json_line) = json_line else {
        return Err(format!("Python bridge 未返回结果：{}", stderr.trim()));
    };

    let mut response: Value = serde_json::from_str(json_line.trim()).map_err(|err| {
        format!(
            "解析 Python bridge 返回失败：{}；stderr：{}",
            err,
            stderr.trim()
        )
    })?;

    if let Some(object) = response.as_object_mut() {
        let logs = stderr
            .lines()
            .filter(|line| !line.trim().is_empty())
            .map(|line| Value::String(line.to_string()))
            .collect();
        object.insert("logs".to_string(), Value::Array(logs));
    }

    if response.get("ok").and_then(Value::as_bool) == Some(true) {
        let mut saved = session
            .0
            .lock()
            .map_err(|_| "工作流会话已锁定".to_string())?;
        *saved = session_payload;
    }
    Ok(response)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(WorkflowSession::default())
        .invoke_handler(tauri::generate_handler![
            run_python_task,
            select_import_file,
            select_dictionary_file,
            select_stopwords_file,
            select_chart_png_path,
            save_chart_png,
            select_output_directory
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
