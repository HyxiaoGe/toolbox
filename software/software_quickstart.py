import subprocess
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QuickstartError(Exception):
    """Custom exception for quickstart errors."""
    pass

def launch_program(executable_path, arguments_list=None):
    if arguments_list is None:
        arguments_list = []
    is_path_like = os.path.sep in executable_path or os.path.altsep in executable_path if os.path.altsep else False
    if is_path_like and not os.path.exists(executable_path):
        msg = f"Executable not found at specified path: {executable_path}"
        logging.error(msg)
        return False, msg

    try:
        if is_path_like:
             cmd_list = [executable_path] + arguments_list
             cmd_to_run = subprocess.list2cmdline(cmd_list)
        else:
             cmd_to_run = executable_path
             if arguments_list:
                 cmd_to_run += " " + " ".join(arguments_list)

        subprocess.Popen(cmd_to_run, shell=True)
        msg = f"Successfully launched: {cmd_to_run}"
        logging.info(msg)
        return True, msg
    except Exception as e:
        msg = f"Failed to launch program '{executable_path}': {e}"
        logging.error(msg, exc_info=True)
        return False, msg

def open_with_default_app(file_path):
    if not os.path.exists(file_path):
        msg = f"File not found: {file_path}"
        logging.error(msg)
        return False, msg
    try:
        os.startfile(file_path)
        msg = f"Attempted to open '{file_path}' with default application."
        logging.info(msg)
        return True, msg
    except AttributeError:
        msg = "os.startfile is not available on this operating system. This function is Windows-specific."
        logging.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Failed to open file '{file_path}' with default app: {e}"
        logging.error(msg, exc_info=True)
        return False, msg

def load_software_config(config_file_path):
    if not os.path.exists(config_file_path):
        msg = f"Configuration file not found: {config_file_path}"
        logging.warning(msg) 
        return None, msg
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        msg = f"Configuration loaded successfully from {config_file_path}."
        logging.info(msg)
        return config_data, msg
    except json.JSONDecodeError as e:
        msg = f"Error decoding JSON from {config_file_path}: {e}"
        logging.error(msg)
        return None, msg
    except Exception as e:
        msg = f"Failed to load configuration from {config_file_path}: {e}"
        logging.error(msg, exc_info=True)
        return None, msg

def execute_custom_action(action_details, log_callback_gui=None):
    action_name = action_details.get("action")
    item_name = action_details.get("name", "Unknown Action Item")

    def log(message):
        logging.info(f"Action '{item_name}' ({action_name}): {message}")
        if log_callback_gui:
            log_callback_gui(message)
    
    log(f"Executing action '{action_name}' for item '{item_name}'.")

    if action_name == "open_default":
        target_file = action_details.get("target_file")
        if not target_file:
            return False, f"'{item_name}': 'target_file' not specified for action 'open_default'."
        log(f"Attempting to open '{target_file}' with default application.")
        return open_with_default_app(target_file)
    
    elif action_name == "run_specific_tool_A":
        param = action_details.get("parameter_X", "default_value")
        log(f"Running specific tool A with parameter: {param}")
        return True, f"Specific tool A executed with {param}."
        
    else:
        msg = f"Unknown action '{action_name}' for item '{item_name}'."
        log(msg)
        return False, msg


if __name__ == '__main__':
    print("--- Testing Software Quickstart Logic ---")
    
    dummy_config_path = "./dummy_software_config.json"
    if not os.path.exists(dummy_config_path):
        dummy_data = {
            "software": [
                {"name": "Notepad", "path": "notepad.exe", "args": []},
                {"name": "Calculator", "path": "calc.exe"},
                {"name": "Open Test Document", "action": "open_default", "target_file": "./test_document.txt"},
                {"name": "Invalid Action Item", "action": "do_something_unknown"}
            ]
        }
        with open(dummy_config_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_data, f, indent=4)
        print(f"Created dummy config: {dummy_config_path}")
        with open("./test_document.txt", "w", encoding='utf-8') as f:
            f.write("This is a test document for the open_default action.")
        print("Created dummy test_document.txt")

    config, load_msg = load_software_config(dummy_config_path)
    print(load_msg)

    if config and "software" in config:
        for item in config["software"]:
            item_name = item.get("name", "Unnamed Item")
            print(f"\nProcessing item: {item_name}")
            if "path" in item:
                success, msg = launch_program(item["path"], item.get("args"))
                print(f"  Launch attempt for '{item_name}': {success} - {msg}")
            elif "action" in item:
                success, msg = execute_custom_action(item, log_callback_gui=lambda x: print(f"  ACTION_LOG: {x}"))
                print(f"  Action execution for '{item_name}': {success} - {msg}")
            else:
                print(f"  Item '{item_name}' has no 'path' or 'action' defined.")
    
    success, msg = open_with_default_app("./non_existent_file.txt")
    success, msg = launch_program("nonexistent_program.exe")
