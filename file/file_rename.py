import os
import re
from datetime import datetime

def generate_rename_plan(folder_path, rename_template, match_pattern_str=None, start_num=1, step_num=1):
    """
    根据模板生成文件重命名计划。
    返回: (成功标志, 计划或错误消息, 日志消息列表)
    plan 是元组列表: [(原始完整路径, 新完整路径), ...]
    """
    logs = []
    plan = []
    current_num = start_num

    if not os.path.isdir(folder_path):
        return False, f"错误: 文件夹 '{folder_path}' 不存在或无效。", [f"错误: 文件夹 '{folder_path}' 不存在或无效。"]

    try:
        match_regex = None
        if match_pattern_str:
            try:
                if any(c in match_pattern_str for c in ['^', '$', '(', ')', '[', ']', '{', '}', '+', '?', '|', '\\']):
                    regex_str = match_pattern_str
                    logs.append(f"使用正则表达式匹配模式: {regex_str}")
                elif '*' in match_pattern_str or '?' in match_pattern_str:
                    regex_str = '^' + match_pattern_str.replace('.', '\\.').replace('*', '.*').replace('?', '.') + '$'
                    logs.append(f"使用转换后的 Glob 匹配模式 (正则): {regex_str}")
                else:
                    regex_str = '^' + re.escape(match_pattern_str) + '$'
                    logs.append(f"使用字面量匹配模式 (正则): {regex_str}")
                match_regex = re.compile(regex_str, re.IGNORECASE)
            except re.error as e:
                err_msg = f"错误: 无效的匹配模式 '{match_pattern_str}': {e}"
                logs.append(err_msg)
                return False, err_msg, logs

        filenames = os.listdir(folder_path)
        filenames.sort()

        temp_new_names_check = set()

        for filename in filenames:
            original_full_path = os.path.join(folder_path, filename)
            if os.path.isdir(original_full_path):
                continue

            if match_regex:
                match_obj = match_regex.search(filename)
                if not match_obj:
                    logs.append(f"  跳过 '{filename}' (与模式不匹配).")
                    continue
            else:
                match_obj = None


            name_part, ext_part = os.path.splitext(filename)
            ext_part = ext_part.lstrip('.')

            # 处理模板
            new_name = rename_template
            new_name = new_name.replace("{{num}}", str(current_num))
            new_name = new_name.replace("{{name}}", name_part)
            new_name = new_name.replace("{{ext}}", ext_part)
            
            now = datetime.now()
            new_name = new_name.replace("{{date}}", now.strftime("%Y-%m-%d"))
            new_name = new_name.replace("{{datetime}}", now.strftime("%Y-%m-%d_%H-%M-%S"))
            
            if match_obj:
                for i in range(match_regex.groups):
                    group_val = match_obj.group(i + 1)
                    if group_val is not None:
                         new_name = new_name.replace(f"{{{{group{i+1}}}}}", group_val)


            new_full_path = os.path.join(folder_path, new_name)

            # 在添加到计划之前检查潜在冲突
            if original_full_path.lower() == new_full_path.lower():
                logs.append(f"  跳过 '{filename}' (新旧名称相同).")
                continue
            
            current_final_name_to_check = new_name
            current_final_path_to_check = new_full_path
            suffix_counter = 1
            while current_final_name_to_check.lower() in temp_new_names_check or \
                  (os.path.exists(current_final_path_to_check) and original_full_path.lower() != current_final_path_to_check.lower()):
                logs.append(f"  警告: 计划的名称 '{current_final_name_to_check}' 与本批次中已计划的名称冲突或磁盘上已存在不同文件。尝试添加后缀。")
                base, ext = os.path.splitext(new_name)
                current_final_name_to_check = f"{base}_{suffix_counter}{ext}"
                current_final_path_to_check = os.path.join(folder_path, current_final_name_to_check)
                suffix_counter += 1
                if suffix_counter > 100:
                    logs.append(f"  错误: 无法为 '{filename}' 生成唯一的新文件名 (基于 '{new_name}')。已尝试100次后缀。跳过。")
                    break
            
            if suffix_counter > 100:
                continue

            new_name = current_final_name_to_check
            new_full_path = current_final_path_to_check


            plan.append((original_full_path, new_full_path))
            temp_new_names_check.add(new_name.lower())
            logs.append(f"  计划: '{filename}' -> '{new_name}'")
            current_num += step_num


        if not plan:
            logs.append("没有文件符合重命名条件或无需重命名。")
        else:
            logs.append(f"重命名计划生成完毕，共 {len(plan)} 个文件。")
        return True, plan, logs

    except Exception as e:
        error_msg = f"生成重命名计划时出错: {e}"
        logs.append(error_msg)
        return False, error_msg, logs

def execute_rename_plan(rename_plan, log_callback=None):
    renamed_count = 0
    error_count = 0
    detailed_logs = []

    def _log(msg):
        detailed_logs.append(msg)
        if log_callback:
            try:
                log_callback(msg)
            except Exception as cb_e:
                detailed_logs.append(f"[Callback Error during log: {cb_e}]")

    if not rename_plan:
        msg = "没有提供重命名计划。"
        _log(msg)
        return True, msg, detailed_logs

    _log(f"开始执行重命名计划，共 {len(rename_plan)} 项操作。")

    for original_path, new_path in rename_plan:
        try:
            if not os.path.exists(original_path):
                _log(f"  错误: 原文件 '{os.path.basename(original_path)}' 在执行时未找到。跳过。")
                error_count += 1
                continue

            if original_path.lower() != new_path.lower() and os.path.exists(new_path):
                _log(f"  错误: 目标文件 '{os.path.basename(new_path)}' 在执行时已存在。跳过重命名 '{os.path.basename(original_path)}' 以避免覆盖。")
                error_count +=1
                continue

            os.rename(original_path, new_path)
            _log(f"  成功: '{os.path.basename(original_path)}' -> '{os.path.basename(new_path)}'")
            renamed_count += 1
        except Exception as e:
            _log(f"  重命名 '{os.path.basename(original_path)}' 为 '{os.path.basename(new_path)}' 失败: {e}")
            error_count += 1

    summary_msg = f"重命名操作完成。成功重命名 {renamed_count} 个文件。"
    if error_count > 0:
        summary_msg += f" {error_count} 个文件重命名失败或被跳过。"
    
    _log(summary_msg)
    all_successful = (error_count == 0 and renamed_count == len(rename_plan)) or (renamed_count > 0 and error_count == 0)
    if len(rename_plan) == 0 and error_count == 0:
        all_successful = True

    return all_successful, summary_msg, detailed_logs


if __name__ == '__main__':
    test_folder_base = r'E:\\test_rename_adv' 

    def setup_test_folder(folder_name, files_to_create):
        folder_path = os.path.join(test_folder_base, folder_name)
        if os.path.exists(folder_path):
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    pass
        else:
            os.makedirs(folder_path)
        
        for fname, content in files_to_create.items():
            with open(os.path.join(folder_path, fname), 'w') as f:
                f.write(content)
        return folder_path

    def print_plan_results(success_plan, plan_or_err, logs_plan):
        print("\nPlan Generation Logs:")
        for log in logs_plan: print(log)
        if success_plan:
            print("Generated Plan:")
            if plan_or_err:
                for orig, new in plan_or_err: print(f"  '{os.path.basename(orig)}' -> '{os.path.basename(new)}'")
            else:
                print("  (No files in plan)")
        else:
            print(f"Plan Generation Failed: {plan_or_err}")
        return success_plan, plan_or_err


    def print_exec_results(success_exec, summary_exec, logs_exec):
        print("\nExecution Logs:")
        for log in logs_exec: print(log)
        print(f"Execution Success Status: {success_exec}, Summary: {summary_exec}")


    print("--- Test 1: Simple Prefix ---")
    files1 = {
        "report_final.txt": "report1", "REPORT_alpha.doc": "report2",
        "image_001.jpg": "image1", "image_002.png": "image2",
        "data_val_03.dat": "data1", "NewFile_1_data.txt": "pre-existing" # 可能冲突的现有文件
    }
    folder1 = setup_test_folder("test1_simple", files1)
    template1 = "NewFile_{{num}}_{{name}}.{{ext}}"
    s_plan1, p_err1, l_plan1 = generate_rename_plan(folder1, template1, start_num=1)
    s_plan1, p_err1 = print_plan_results(s_plan1, p_err1, l_plan1)
    if s_plan1 and p_err1: # Only execute if plan is valid and has items
        s_exec1, sum_exec1, l_exec1 = execute_rename_plan(p_err1, log_callback=lambda msg: print(f"  EXEC_LOG: {msg}"))
        print_exec_results(s_exec1, sum_exec1, l_exec1)

    print("\n\n--- Test 2: Match Pattern (images) and numbering ---")
    files2 = {
        "OldImage_A.jpg": "imgA", "OldImage_B.png": "imgB", "document.txt": "doc",
        "Vacation Photo 1.jpeg": "photo1", "Vacation Photo 2.JPG": "photo2"
    }
    folder2 = setup_test_folder("test2_match", files2)
    template2 = "Photo_{{num}}.{{ext}}"
    match_pat_2 = "*.jp*g"
    s_plan2, p_err2, l_plan2 = generate_rename_plan(folder2, template2, match_pattern_str=match_pat_2, start_num=100, step_num=2)
    s_plan2, p_err2 = print_plan_results(s_plan2, p_err2, l_plan2)
    if s_plan2 and p_err2:
        s_exec2, sum_exec2, l_exec2 = execute_rename_plan(p_err2, log_callback=lambda msg: print(f"  EXEC_LOG: {msg}"))
        print_exec_results(s_exec2, sum_exec2, l_exec2)

    print("\n\n--- Test 3: Regex capture groups ---")
    files3 = {
        "song_artistA_title1_version2.mp3": "s1", "song_artistB_title_final.wav": "s2",
        "clip_showX_episode3_segment1.mkv": "c1", "randomfile.txt": "r1"
    }
    folder3 = setup_test_folder("test3_regex", files3)
    template3 = "{{group1}} - {{group2}} ({{num}}).{{ext}}" 
    match_pat_3 = r"song_([^_]+)_([^.]+)(\S*)\.(mp3|wav)"
    s_plan3, p_err3, l_plan3 = generate_rename_plan(folder3, template3, match_pattern_str=match_pat_3, start_num=1)
    s_plan3, p_err3 = print_plan_results(s_plan3, p_err3, l_plan3)
    if s_plan3 and p_err3:
        s_exec3, sum_exec3, l_exec3 = execute_rename_plan(p_err3, log_callback=lambda msg: print(f"  EXEC_LOG: {msg}"))
        print_exec_results(s_exec3, sum_exec3, l_exec3)

    print("\n\n--- Test 4: No matching files ---")
    files4 = {"file.txt": "text"}
    folder4 = setup_test_folder("test4_nomatch", files4)
    template4 = "NoMatch_{{num}}.{{ext}}"
    match_pat_4 = "*.log"
    s_plan4, p_err4, l_plan4 = generate_rename_plan(folder4, template4, match_pattern_str=match_pat_4)
    s_plan4, p_err4 = print_plan_results(s_plan4, p_err4, l_plan4)
    if s_plan4 and p_err4:
         s_exec4, sum_exec4, l_exec4 = execute_rename_plan(p_err4, log_callback=lambda msg: print(f"  EXEC_LOG: {msg}"))
         print_exec_results(s_exec4, sum_exec4, l_exec4)
    elif s_plan4 and not p_err4:
        print("  (No files in plan, execution skipped)")


    print("\n\n--- Test 5: Name Collision ---")
    files5 = {
        "a.txt": "1", "b.txt": "2", 
        "target.txt": "existing_target"
    }
    folder5 = setup_test_folder("test5_collision", files5)
    template5_1 = "target.{{ext}}"
    template5_1 = "target.{{ext}}"
    s_plan5_1, p_err5_1, l_plan5_1 = generate_rename_plan(folder5, template5_1, match_pattern_str="*.txt")
    s_plan5_1, p_err5_1 = print_plan_results(s_plan5_1, p_err5_1, l_plan5_1)
    if s_plan5_1 and p_err5_1:
        s_exec5_1, sum_exec5_1, l_exec5_1 = execute_rename_plan(p_err5_1, log_callback=lambda msg: print(f"  EXEC_LOG: {msg}"))
        print_exec_results(s_exec5_1, sum_exec5_1, l_exec5_1)