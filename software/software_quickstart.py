import subprocess
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QuickstartError(Exception):
    """Custom exception for quickstart errors."""
    pass

def launch_program(executable_path, arguments_list=None):
    """
    Launches a program with given arguments.
    executable_path: Full path to the executable or just the executable name (e.g., "notepad.exe").
    arguments_list: A list of string arguments for the executable.
    Returns: (bool success, str message)
    """
    if arguments_list is None:
        arguments_list = []
    
    # If executable_path is a simple name (not a path) and doesn't exist directly,
    # we'll rely on shell=True and system PATH to find it.
    # If it's a path and doesn't exist, then it's an error.
    is_path_like = os.path.sep in executable_path or os.path.altsep in executable_path if os.path.altsep else False # Check for path separators
    if is_path_like and not os.path.exists(executable_path):
        msg = f"Executable not found at specified path: {executable_path}"
        logging.error(msg)
        return False, msg

    try:
        # For executables like 'notepad.exe', just using the name with shell=True
        # allows the system to find it in PATH.
        # If executable_path is already a full path, shell=True is generally fine too.
        # The command passed to Popen should be a string if shell=True for quoting safety.
        if is_path_like: # If it's a path, construct cmd list as before
             cmd_list = [executable_path] + arguments_list
             cmd_to_run = subprocess.list2cmdline(cmd_list) # More robust way to form command string for shell=True
        else: # If just an exe name, build the command string directly
             cmd_to_run = executable_path
             if arguments_list:
                 cmd_to_run += " " + " ".join(arguments_list) # Simple space separation, consider shlex for complex args

        subprocess.Popen(cmd_to_run, shell=True)
        msg = f"Successfully launched: {cmd_to_run}"
        logging.info(msg)
        return True, msg
    except Exception as e:
        msg = f"Failed to launch program '{executable_path}': {e}"
        logging.error(msg, exc_info=True)
        return False, msg

def open_with_default_app(file_path):
    """
    Opens a file with its default system application (Windows specific using os.startfile).
    file_path: Full path to the file.
    Returns: (bool success, str message)
    """
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
        # Fallback for non-Windows could be implemented here if needed, e.g., using xdg-open on Linux
        # For now, return False
        return False, msg
    except Exception as e:
        msg = f"Failed to open file '{file_path}' with default app: {e}"
        logging.error(msg, exc_info=True)
        return False, msg

def load_software_config(config_file_path):
    """
    Loads software configuration from a JSON file.
    config_file_path: Path to the JSON configuration file.
    Returns: (dict config_data or None, str message)
    """
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

# Example of handling a custom action defined in software_config.json
# This function would be called by the GUI if an item has an "action" key.
def execute_custom_action(action_details, log_callback_gui=None):
    """
    Executes a custom action based on action_details from config.
    action_details: A dictionary for the item, e.g., {"name": "Open My Document", "action": "open_default", "target_file": "path/to/doc.txt"}
    log_callback_gui: Optional function to send log messages to GUI.
    Returns: (bool success, str message)
    """
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
    
    elif action_name == "run_specific_tool_A": # Example of a more complex, hardcoded action
        # This is where you might put logic that was previously in a placeholder like quick_start_logic
        # For example, trigger some other script or internal function.
        param = action_details.get("parameter_X", "default_value")
        log(f"Running specific tool A with parameter: {param}")
        # ... actual logic for tool A ...
        return True, f"Specific tool A executed with {param}."
        
    # Add more custom actions here as elif blocks

    else:
        msg = f"Unknown action '{action_name}' for item '{item_name}'."
        log(msg)
        return False, msg


if __name__ == '__main__':
    print("--- Testing Software Quickstart Logic ---")
    
    # Test config loading
    # Create a dummy config for testing if it doesn't exist
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
        # Create a dummy test document
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
                # Pass a simple print function as the GUI log callback for this test
                success, msg = execute_custom_action(item, log_callback_gui=lambda x: print(f"  ACTION_LOG: {x}"))
                print(f"  Action execution for '{item_name}': {success} - {msg}")
            else:
                print(f"  Item '{item_name}' has no 'path' or 'action' defined.")
    
    # Test non-existent file for default open
    print("\nTesting open_with_default_app with non-existent file:")
    success, msg = open_with_default_app("./non_existent_file.txt")
    print(f"  Result: {success} - {msg}")

    # Test launching a non-existent program
    print("\nTesting launch_program with non-existent executable:")
    success, msg = launch_program("nonexistent_program.exe")
    print(f"  Result: {success} - {msg}")

    # Clean up dummy files
    # if os.path.exists(dummy_config_path): os.remove(dummy_config_path)
    # if os.path.exists("./test_document.txt"): os.remove("./test_document.txt")
    # print("\nCleaned up dummy files (if they were created by this test run).")
    print("\nNote: Actual launching of notepad/calc may open windows.")
    print("If dummy files were created, you might want to manually delete them if not cleaned up automatically.")
