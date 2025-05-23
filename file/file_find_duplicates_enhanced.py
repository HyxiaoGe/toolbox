import os
import shutil
import hashlib
import subprocess
from pathlib import Path
from PIL import Image
import imagehash
from collections import defaultdict
import logging
import re
from difflib import SequenceMatcher
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DuplicateLevel(Enum):
    """重复程度等级"""
    CERTAIN = "确定重复"
    HIGHLY_SUSPECTED = "高度疑似"
    MODERATELY_SUSPECTED = "中度疑似"
    LOWLY_SUSPECTED = "低度疑似"

@dataclass
class FileMetadata:
    """文件元数据"""
    path: str
    size: int
    duration: Optional[float] = None  # 视频时长（秒）
    content_hash: Optional[str] = None  # 内容哈希
    sample_hash: Optional[str] = None  # 采样哈希（用于视频）
    perceptual_hash: Optional[str] = None  # 感知哈希（用于图片）
    filename_normalized: Optional[str] = None  # 标准化文件名

@dataclass
class DuplicateGroup:
    """重复文件组"""
    level: DuplicateLevel
    score: float
    files: List[FileMetadata]
    reasons: List[str]  # 判定为重复的原因

class EnhancedDuplicateFinder:
    """增强版重复文件查找器"""
    
    def __init__(self, ffprobe_path: str = None, 
                 log_callback: Optional[callable] = None, 
                 stop_event: Optional[threading.Event] = None):
        self.ffprobe_path = ffprobe_path or self._find_ffprobe()
        self.video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v', '.3gp', '.webm'}
        self.image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}
        self.log_callback = log_callback
        self.stop_event = stop_event or threading.Event()
        
        # 评分权重
        self.weights = {
            'content_hash_match': 100,  # 内容哈希完全相同
            'sample_hash_match': 80,    # 采样哈希相同
            'perceptual_hash_match': 70, # 感知哈希相同
            'size_match': 40,           # 文件大小相同
            'duration_match': 35,       # 时长相同（±2秒）
            'filename_high_similarity': 20,  # 文件名高度相似
            'filename_copy_pattern': 15,     # 文件名包含复制模式
            'filename_moderate_similarity': 10,  # 文件名中度相似
        }
        
        # 评分阈值
        self.thresholds = {
            DuplicateLevel.CERTAIN: 80,
            DuplicateLevel.HIGHLY_SUSPECTED: 60,
            DuplicateLevel.MODERATELY_SUSPECTED: 40,
            DuplicateLevel.LOWLY_SUSPECTED: 20,
        }

    def _log(self, message: str, level: str = "INFO"):
        """统一日志记录，支持回调"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            if level == "ERROR":
                logging.error(message)
            elif level == "WARNING":
                logging.warning(message)
            else:
                logging.info(message)

    def _check_stop_event(self):
        """检查是否需要停止"""
        if self.stop_event and self.stop_event.is_set():
            self._log("收到停止信号，操作已中止。", "WARNING")
            raise InterruptedError("操作被用户中止")

    def _find_ffprobe(self) -> Optional[str]:
        """尝试找到ffprobe路径"""
        common_paths = [
            r'D:\ffmpeg\bin\ffprobe.exe',
            r'D:\ffmpeg-7.0-full_build\bin\ffprobe.exe',
            r'C:\ffmpeg\bin\ffprobe.exe',
            'ffprobe.exe',
            'ffprobe'
        ]
        
        for path in common_paths:
            if shutil.which(path) or os.path.isfile(path):
                return path
        return None

    def get_video_duration(self, file_path: str) -> Optional[float]:
        """获取视频时长"""
        if not self.ffprobe_path:
            self._log(f"ffprobe路径未设置，无法获取视频时长: {file_path}", "WARNING")
            return None
            
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-v", "error", "-show_entries", 
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            self._log(f"无法获取视频时长 {file_path}: {e}", "WARNING")
        return None

    def calculate_content_hash(self, filepath: str) -> Optional[str]:
        """计算文件完整内容哈希"""
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(65536):
                    self._check_stop_event()
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self._log(f"计算内容哈希失败 {filepath}: {e}", "ERROR")
            return None

    def calculate_sample_hash(self, filepath: str, sample_size_mb: int = 5) -> Optional[str]:
        """计算视频采样哈希"""
        hasher = hashlib.sha256()
        try:
            file_size = os.path.getsize(filepath)
            sample_bytes = sample_size_mb * 1024 * 1024
            chunk_size = 65536

            with open(filepath, 'rb') as f:
                if file_size <= sample_bytes:
                    # 小文件，读取全部
                    while chunk := f.read(chunk_size):
                        self._check_stop_event()
                        hasher.update(chunk)
                else:
                    # 大文件，采样读取：开头、中间、结尾
                    # 开头
                    for _ in range(sample_bytes // (3 * chunk_size)):
                        self._check_stop_event()
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        hasher.update(chunk)
                    
                    # 中间
                    f.seek(file_size // 2 - (sample_bytes // 6))
                    for _ in range(sample_bytes // (3 * chunk_size)):
                        self._check_stop_event()
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        hasher.update(chunk)
                    
                    # 结尾
                    f.seek(max(0, file_size - (sample_bytes // 3)))
                    for _ in range(sample_bytes // (3 * chunk_size)):
                        self._check_stop_event()
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        hasher.update(chunk)
            
            return hasher.hexdigest()
        except Exception as e:
            self._log(f"计算采样哈希失败 {filepath}: {e}", "ERROR")
            return None

    def calculate_perceptual_hash(self, filepath: str) -> Optional[str]:
        """计算图片感知哈希"""
        try:
            with Image.open(filepath) as img:
                # 使用更高精度的感知哈希
                img_hash = imagehash.average_hash(
                    img.convert("L").resize((32, 32), Image.Resampling.LANCZOS)
                )
                return str(img_hash)
        except Exception as e:
            self._log(f"计算感知哈希失败 {filepath}: {e}", "WARNING")
            return None

    def normalize_filename(self, filepath: str) -> str:
        """标准化文件名，移除常见的重复标记"""
        filename = Path(filepath).stem.lower()
        
        # 移除常见的重复模式
        patterns = [
            r'[\s_-]*copy[\s_-]*\d*$',
            r'[\s_-]*副本[\s_-]*\d*$',
            r'[\s_-]*\(\d+\)$',
            r'[\s_-]*\[\d+\]$',
            r'[\s_-]*_\d+$',
            r'[\s_-]*-\d+$',
        ]
        
        for pattern in patterns:
            filename = re.sub(pattern, '', filename, flags=re.IGNORECASE)
        
        # 移除多余的空格和特殊字符
        filename = re.sub(r'[\s_-]+', '_', filename).strip('_')
        
        return filename

    def calculate_filename_similarity(self, name1: str, name2: str) -> float:
        """计算文件名相似度"""
        norm1 = self.normalize_filename(name1)
        norm2 = self.normalize_filename(name2)
        
        # 标准化后完全相同
        if norm1 == norm2:
            return 1.0
        
        # 计算字符串相似度
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity

    def has_copy_pattern(self, filepath: str) -> bool:
        """检查文件名是否包含复制模式"""
        filename = Path(filepath).stem.lower()
        patterns = [
            r'copy\d*$', r'副本\d*$', r'\(\d+\)$', r'\[\d+\]$',
            r'_\d+$', r'-\d+$', r'_copy$', r'-copy$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, filename):
                return True
        return False

    def extract_file_metadata(self, filepath: str) -> FileMetadata:
        """提取文件元数据"""
        self._log(f"提取元数据: {filepath}", "DEBUG")
        try:
            file_size = os.path.getsize(filepath)
            ext = Path(filepath).suffix.lower()
            
            metadata = FileMetadata(
                path=filepath,
                size=file_size,
                filename_normalized=self.normalize_filename(filepath)
            )
            
            if ext in self.video_extensions:
                # 视频文件
                metadata.duration = self.get_video_duration(filepath)
                metadata.sample_hash = self.calculate_sample_hash(filepath)
                
            elif ext in self.image_extensions:
                # 图片文件
                metadata.perceptual_hash = self.calculate_perceptual_hash(filepath)
                # 小图片文件也计算完整哈希
                if file_size < 10 * 1024 * 1024:  # 小于10MB
                    metadata.content_hash = self.calculate_content_hash(filepath)
                    
            else:
                # 其他文件
                metadata.content_hash = self.calculate_content_hash(filepath)
            
            return metadata
            
        except Exception as e:
            self._log(f"提取文件元数据失败 {filepath}: {e}", "ERROR")
            return FileMetadata(path=filepath, size=0)

    def calculate_similarity_score(self, file1: FileMetadata, file2: FileMetadata) -> Tuple[float, List[str]]:
        """计算两个文件的相似度分数"""
        score = 0.0
        reasons = []
        
        # 内容哈希匹配（最高优先级）
        if file1.content_hash and file2.content_hash and file1.content_hash == file2.content_hash:
            score += self.weights['content_hash_match']
            reasons.append("内容哈希完全相同")
            return score, reasons  # 内容哈希相同就是确定重复
        
        # 采样哈希匹配（视频）
        if file1.sample_hash and file2.sample_hash and file1.sample_hash == file2.sample_hash:
            score += self.weights['sample_hash_match']
            reasons.append("视频采样哈希相同")
        
        # 感知哈希匹配（图片）
        if file1.perceptual_hash and file2.perceptual_hash:
            # 计算汉明距离
            try:
                hash1 = imagehash.hex_to_hash(file1.perceptual_hash)
                hash2 = imagehash.hex_to_hash(file2.perceptual_hash)
                hamming_distance = hash1 - hash2
                
                if hamming_distance <= 2:  # 非常相似
                    score += self.weights['perceptual_hash_match']
                    reasons.append(f"图片感知哈希相似(距离:{hamming_distance})")
                elif hamming_distance <= 5:  # 比较相似
                    score += self.weights['perceptual_hash_match'] * 0.7
                    reasons.append(f"图片感知哈希较相似(距离:{hamming_distance})")
            except:
                pass
        
        # 文件大小匹配
        if file1.size == file2.size and file1.size > 0:
            score += self.weights['size_match']
            reasons.append("文件大小相同")
        
        # 视频时长匹配
        if file1.duration and file2.duration:
            duration_diff = abs(file1.duration - file2.duration)
            if duration_diff <= 2.0:  # 2秒误差内
                score += self.weights['duration_match']
                reasons.append(f"视频时长相近(差异:{duration_diff:.1f}秒)")
            elif duration_diff <= 5.0:  # 5秒误差内
                score += self.weights['duration_match'] * 0.7
                reasons.append(f"视频时长较接近(差异:{duration_diff:.1f}秒)")
        
        # 文件名相似度
        filename_similarity = self.calculate_filename_similarity(file1.path, file2.path)
        if filename_similarity >= 0.9:
            score += self.weights['filename_high_similarity']
            reasons.append(f"文件名高度相似({filename_similarity:.2f})")
        elif filename_similarity >= 0.7:
            score += self.weights['filename_moderate_similarity']
            reasons.append(f"文件名中度相似({filename_similarity:.2f})")
        
        # 复制模式检测
        if self.has_copy_pattern(file1.path) or self.has_copy_pattern(file2.path):
            score += self.weights['filename_copy_pattern']
            reasons.append("文件名包含复制标记")
        
        return score, reasons

    def determine_duplicate_level(self, score: float) -> Optional[DuplicateLevel]:
        """根据分数确定重复等级"""
        for level, threshold in self.thresholds.items():
            if score >= threshold:
                return level
        return None

    def group_files_by_characteristics(self, files: List[FileMetadata]) -> Dict[str, List[FileMetadata]]:
        """按特征预分组文件，提高比较效率"""
        groups = defaultdict(list)
        
        for file_meta in files:
            # 按文件大小和类型分组
            ext = Path(file_meta.path).suffix.lower()
            key = f"{ext}_{file_meta.size}"
            groups[key].append(file_meta)
        
        # 只保留有多个文件的组
        return {k: v for k, v in groups.items() if len(v) > 1}

    def find_duplicates_in_directory(self, directory_path: str) -> Dict[DuplicateLevel, List[DuplicateGroup]]:
        """在指定目录中查找重复文件 (核心逻辑)"""
        self._log(f"开始扫描目录: {directory_path}", "INFO")
        all_files_metadata: List[FileMetadata] = []
        
        for root, _, files in os.walk(directory_path):
            self._check_stop_event()
            for file in files:
                self._check_stop_event()
                filepath = os.path.join(root, file)
                try:
                    metadata = self.extract_file_metadata(filepath)
                    if metadata:
                        all_files_metadata.append(metadata)
                except Exception as e:
                    self._log(f"提取元数据失败 {filepath}: {e}", "ERROR")

        self._log(f"共收集到 {len(all_files_metadata)} 个文件的元数据。", "INFO")
        if not all_files_metadata:
            return {}

        # 预筛选和分组 (示例：按大小)
        # self._log("按文件大小进行初步分组...", "DEBUG")
        # files_by_size = defaultdict(list)
        # for meta in all_files_metadata:
        #     files_by_size[meta.size].append(meta)
        
        # potential_groups_after_size_filter = {k: v for k, v in files_by_size.items() if len(v) > 1}
        # self._log(f"按大小筛选后，剩下 {len(potential_groups_after_size_filter)} 组，共 {sum(len(v) for v in potential_groups_after_size_filter.values())} 个文件需要进一步比较。", "DEBUG")

        # 替换为更全面的预分组策略
        # grouped_by_characteristics = self.group_files_by_characteristics(all_files_metadata)
        # self._log(f"按特征（大小、短哈希等）分组后，有 {len(grouped_by_characteristics)} 个潜在重复特征组。", "DEBUG")

        # 优化：直接进行两两比较，但只在有意义的子集上进行
        # 实际的比较和分组逻辑
        potential_duplicate_pairs: List[Tuple[FileMetadata, FileMetadata, float, List[str]]] = []
        
        # Create a copy for iteration while potentially modifying all_files_metadata or related structures
        # For now, we iterate over a static list derived from initial scan.
        # Optimization: Sort by size first to quickly rule out non-matches.
        sorted_metadata = sorted(all_files_metadata, key=lambda m: m.size)
        
        num_files_to_compare = len(sorted_metadata)
        self._log(f"开始比较 {num_files_to_compare} 个文件之间的相似性...", "INFO")
        
        processed_count = 0
        for i in range(num_files_to_compare):
            self._check_stop_event()
            file1 = sorted_metadata[i]
            # Only compare with subsequent files to avoid redundant comparisons (j > i)
            # and files with the same size (optimization)
            for j in range(i + 1, num_files_to_compare):
                self._check_stop_event()
                file2 = sorted_metadata[j]

                # Optimization: If sizes are different, they cannot be CERTAIN duplicates based on content hash or even sample hash.
                # Perceptual hashes for images, or filename similarity for videos might still apply.
                # For now, let's keep it simple: if size differs, assume they are less likely to be strong duplicates.
                # A more robust approach would be to let calculate_similarity_score handle all checks.
                if file1.size != file2.size and not (file1.perceptual_hash and file2.perceptual_hash): # Allow different size for images
                    continue

                score, reasons = self.calculate_similarity_score(file1, file2)
                level = self.determine_duplicate_level(score)
                
                if level: # Only consider if a duplicate level is assigned
                    potential_duplicate_pairs.append((file1, file2, score, reasons))
            
            processed_count +=1
            if processed_count % 100 == 0 or processed_count == num_files_to_compare:
                 self._log(f"已比较 {processed_count}/{num_files_to_compare} 个文件...", "DEBUG")


        self._log(f"初步找到 {len(potential_duplicate_pairs)} 对潜在重复文件。", "DEBUG")
        if not potential_duplicate_pairs:
            self._log("未发现任何潜在的重复文件对。", "INFO")
            return {}

        # 使用 Disjoint Set Union (DSU) 来合并重叠的重复组
        parent = {meta.path: meta.path for meta in all_files_metadata}
        group_scores = defaultdict(lambda: (0.0, [])) # Stores (max_score, reasons_list) for a group representative

        def find(p_item):
            if parent[p_item] == p_item:
                return p_item
            parent[p_item] = find(parent[p_item])
            return parent[p_item]

        def union(p_item1, p_item2, p_score, p_reasons):
            root1 = find(p_item1)
            root2 = find(p_item2)
            if root1 != root2:
                # Merge smaller tree into larger, or based on some other criteria if needed
                parent[root2] = root1
                # Update score for the new merged group representative (root1)
                # We take the maximum score seen for any pair that formed this group
                current_max_score_root1, current_reasons_root1 = group_scores[root1]
                new_max_score = max(current_max_score_root1, p_score)
                # Aggregate unique reasons
                updated_reasons = list(set(current_reasons_root1 + p_reasons))
                group_scores[root1] = (new_max_score, updated_reasons)
                # Also update for root2 as it's now part of root1's group.
                # This ensures if root2 was a representative, its score info is now under root1.
                del group_scores[root2] # remove score for the merged root

            else: # Already in the same group, just update score and reasons if this pair provides a higher score or new reasons
                current_max_score_root, current_reasons_root = group_scores[root1]
                new_max_score = max(current_max_score_root, p_score)
                updated_reasons = list(set(current_reasons_root + p_reasons))
                group_scores[root1] = (new_max_score, updated_reasons)


        # Initialize scores for individual items before union operations
        for meta in all_files_metadata:
            group_scores[meta.path] = (0.0, []) # Default score, no reasons yet

        for file1, file2, score, reasons in potential_duplicate_pairs:
            union(file1.path, file2.path, score, reasons)
            # Ensure both files are initially in group_scores if not already by individual init
            if file1.path not in group_scores: group_scores[file1.path] = (0.0, [])
            if file2.path not in group_scores: group_scores[file2.path] = (0.0, [])
            
            # Update scores for the representatives after union
            # The score for the representative of the merged group should reflect the highest score
            # and all reasons that led to this grouping.
            rep1 = find(file1.path)
            rep2 = find(file2.path) # Should be same as rep1 after union
            
            # Update score for the representative of the current pair's group
            current_max_score, current_reasons = group_scores[rep1]
            new_max_score = max(current_max_score, score)
            updated_reasons = list(set(current_reasons + reasons))
            group_scores[rep1] = (new_max_score, updated_reasons)


        # 构建最终的组
        final_groups_map = defaultdict(list)
        for meta in all_files_metadata:
            root = find(meta.path)
            final_groups_map[root].append(meta)

        self.duplicate_groups_categorized: Dict[DuplicateLevel, List[DuplicateGroup]] = defaultdict(list)
        
        final_group_objects: List[DuplicateGroup] = []
        for representative_path, files_in_group_meta in final_groups_map.items():
            if len(files_in_group_meta) > 1:
                # Score and reasons are now stored against the representative path in group_scores
                group_score, group_reasons = group_scores[representative_path]
                
                # Determine level based on the final aggregated score for the group
                final_group_level = self.determine_duplicate_level(group_score)
                if not final_group_level: # Should not happen if score > 0 and pairs were found
                    final_group_level = DuplicateLevel.LOWLY_SUSPECTED # Fallback

                group_obj = DuplicateGroup(
                    level=final_group_level,
                    score=group_score,
                    files=files_in_group_meta,
                    reasons=group_reasons if group_reasons else ["Unknown similarity"]
                )
                final_group_objects.append(group_obj)
        
        # Merge overlapping groups based on shared files (though DSU should mostly handle this)
        # merged_groups = self._merge_overlapping_groups(final_group_objects)
        # For now, assume DSU has created distinct groups
        merged_groups = final_group_objects


        for group_obj in merged_groups:
            if len(group_obj.files) > 1: # Only consider groups with more than one file as duplicates
                self.duplicate_groups_categorized[group_obj.level].append(group_obj)
            elif len(group_obj.files) == 1 and hasattr(self, 'include_single_files_in_results') and self.include_single_files_in_results: # For debugging
                 self.duplicate_groups_categorized[DuplicateLevel.NOT_DUPLICATE].append(group_obj)

        # Log details of categorized duplicate groups before returning
        if self.log_callback:
            self._log("[EnhancedFinder] 准备返回结果。各级别重复组 (文件数 > 1) 统计如下：", "DEBUG")
            found_any = False
            for level, groups_in_level in self.duplicate_groups_categorized.items():
                actual_groups = [g for g in groups_in_level if len(g.files) > 1]
                if actual_groups:
                    found_any = True
                    self._log(f"  - 等级 '{level.name}': {len(actual_groups)} 组", "DEBUG")
                    for idx, group_obj in enumerate(actual_groups):
                        self._log(f"    - 组 {idx+1}: Score={group_obj.score:.1f}, Files={len(group_obj.files)}, Reasons={group_obj.reasons}", "TRACE") # TRACE for potentially verbose output
            if not found_any:
                self._log("[EnhancedFinder] 核心逻辑未发现任何有效重复组 (文件数 > 1)。", "DEBUG")
        
        return self.duplicate_groups_categorized

    def _merge_overlapping_groups(self, groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
        """合并有重叠文件的组"""
        if not groups:
            return []
        
        merged = []
        for group in groups:
            merged_with_existing = False
            
            for existing in merged:
                # 检查是否有重叠的文件
                existing_paths = {f.path for f in existing.files}
                group_paths = {f.path for f in group.files}
                
                if existing_paths & group_paths:  # 有交集
                    # 合并组
                    all_files = {f.path: f for f in existing.files + group.files}
                    existing.files = list(all_files.values())
                    existing.score = max(existing.score, group.score)
                    existing.reasons.extend(group.reasons)
                    merged_with_existing = True
                    break
            
            if not merged_with_existing:
                merged.append(group)
        
        return merged

    def print_results(self, results: Dict[DuplicateLevel, List[DuplicateGroup]]):
        """打印结果"""
        if not results:
            print("没有找到重复文件。")
            return
        
        total_groups = sum(len(groups) for groups in results.values())
        total_files = sum(len(group.files) for groups in results.values() for group in groups)
        
        print(f"\n=== 重复文件检测结果 ===")
        print(f"总共找到 {total_groups} 组重复文件，涉及 {total_files} 个文件\n")
        
        for level in [DuplicateLevel.CERTAIN, DuplicateLevel.HIGHLY_SUSPECTED, 
                     DuplicateLevel.MODERATELY_SUSPECTED, DuplicateLevel.LOWLY_SUSPECTED]:
            if level in results and results[level]:
                print(f"【{level.value}】({len(results[level])} 组):")
                
                for i, group in enumerate(results[level], 1):
                    print(f"  组 {i} (评分: {group.score:.1f}):")
                    print(f"    原因: {', '.join(set(group.reasons))}")
                    for file_meta in group.files:
                        size_mb = file_meta.size / (1024 * 1024)
                        duration_str = f", 时长: {file_meta.duration:.1f}s" if file_meta.duration else ""
                        print(f"    - {file_meta.path} ({size_mb:.1f}MB{duration_str})")
                    print()

    def _get_video_duration(self, file_path: str) -> Optional[float]:
        """获取视频时长"""
        if not self.ffprobe_path:
            self._log(f"ffprobe路径未设置，无法获取视频时长: {file_path}", "WARNING")
            return None
            
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-v", "error", "-show_entries", 
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            self._log(f"无法获取视频时长 {file_path}: {e}", "WARNING")
        return None

def find_duplicates_enhanced(folders_to_scan: List[str], move_them: bool = False, 
                            ffprobe_path: str = None, 
                            log_callback: Optional[callable] = None,
                            stop_event: Optional[threading.Event] = None) -> Tuple[List[str], Dict]:
    """
    增强版重复文件查找函数，与原版接口兼容
    
    Args:
        folders_to_scan: 要扫描的文件夹列表
        move_them: 是否移动重复文件
        ffprobe_path: ffprobe路径（可选）
        log_callback: 实时日志回调 (新增)
        stop_event: 终止事件 (新增)
    
    Returns:
        (日志列表, 重复文件组字典)
    """
    finder = EnhancedDuplicateFinder(ffprobe_path, 
                                     log_callback=log_callback, 
                                     stop_event=stop_event)
    all_logs = []
    all_duplicate_groups = {}
    
    def _local_log(message, level="INFO"):
        prefix = f"[{level}] " if level != "INFO" else ""
        all_logs.append(f"{prefix}{message}")
        if log_callback:
            log_callback(message, level)

    if not folders_to_scan:
        _local_log("错误: 未提供要扫描的文件夹。", "ERROR")
        return all_logs, {}
    
    primary_scan_folder = folders_to_scan[0]
    
    # 扫描所有文件夹
    for folder_path in folders_to_scan:
        _local_log(f"--- 开始处理文件夹: {folder_path} ---", "INFO")
        
        try:
            results = finder.find_duplicates_in_directory(folder_path)
            
            # 转换结果格式以兼容原版
            for level, groups in results.items():
                level_name = level.value
                _local_log(f"【{level_name}】找到 {len(groups)} 组", "INFO")
                
                for group in groups:
                    # 使用组的最高分数作为哈希键
                    group_key = f"{level_name}_{group.score:.1f}_{len(group.files)}"
                    file_paths = [f.path for f in group.files]
                    
                    all_duplicate_groups[group_key] = file_paths
                    
                    _local_log(f"  组 (评分: {group.score:.1f}):", "DETAIL")
                    _local_log(f"    原因: {', '.join(set(group.reasons))}", "DETAIL")
                    for file_meta in group.files:
                        size_mb = file_meta.size / (1024 * 1024)
                        duration_str = f", 时长: {file_meta.duration:.1f}s" if file_meta.duration else ""
                        _local_log(f"    - {file_meta.path} ({size_mb:.1f}MB{duration_str})", "DETAIL")
                        
        except InterruptedError:
            _local_log("查找操作被用户中止。", "WARNING")
            return all_logs, {}
        except Exception as e:
            error_msg = f"处理文件夹 {folder_path} 时出错: {e}"
            _local_log(error_msg, "ERROR")
    
    # 统计结果
    if not all_duplicate_groups:
        _local_log("所有扫描的文件夹中均未找到重复文件。", "INFO")
    else:
        num_groups = len(all_duplicate_groups)
        num_files = sum(len(paths) for paths in all_duplicate_groups.values())
        _local_log(f"在所有文件夹中总共找到 {num_groups} 组重复文件，涉及 {num_files} 个文件。", "INFO")
        
        if move_them:
            # 如果需要移动文件，使用原有的移动逻辑
            from . import file_find_duplicates  # 导入原模块
            _local_log(f"--- 开始移动重复文件到 '{os.path.join(primary_scan_folder, 'duplicates_found')}' ---", "INFO")
            
            # 转换格式为原版兼容格式
            legacy_groups = {}
            for group_key, file_paths in all_duplicate_groups.items():
                if len(file_paths) > 1:
                    # 使用简单哈希作为键
                    simple_hash = hashlib.md5(group_key.encode()).hexdigest()
                    legacy_groups[simple_hash] = file_paths
            
            move_logs, moved_count = file_find_duplicates.move_files_to_duplicate_folder(
                legacy_groups, primary_scan_folder
            )
            all_logs.extend(move_logs)
            _local_log(f"总共移动了 {moved_count} 个文件。", "INFO")
        else:
            _local_log("未执行文件移动操作（move_them=False）。", "INFO")
    
    return all_logs, all_duplicate_groups

def collect_duplicate_files_info_enhanced(directory_path: str, 
                                        ffprobe_path: str = None, 
                                        log_callback: Optional[callable] = None,
                                        stop_event: Optional[threading.Event] = None) -> Tuple[Dict, List[str], int, int, int]:
    """
    增强版重复文件信息收集函数，与原版接口兼容
    
    Args:
        log_callback: 实时日志回调 (新增)
        stop_event: 终止事件 (新增)

    Returns:
        (重复文件组字典, 日志列表, 处理文件数, 跳过不支持文件数, 哈希错误文件数)
    """
    finder = EnhancedDuplicateFinder(ffprobe_path, 
                                     log_callback=log_callback, 
                                     stop_event=stop_event)
    logs = []
    processed_files = 0
    skipped_unsupported = 0
    skipped_hash_errors = 0
    
    def _local_log(message, level="INFO"):
        prefix = f"[{level}] " if level != "INFO" else ""
        logs.append(f"{prefix}{message}")
        if log_callback:
            log_callback(message, level)

    if not os.path.isdir(directory_path):
        _local_log(f"错误: 提供的路径不是一个有效的目录: {directory_path}", "ERROR")
        return {}, logs, processed_files, skipped_unsupported, skipped_hash_errors
    
    _local_log(f"开始扫描目录 (增强版): {directory_path}", "INFO")
    
    try:
        results = finder.find_duplicates_in_directory(directory_path)
        
        # 统计处理的文件（可以从finder内部获取，或者保持外部统计）
        for root, _, files_in_dir in os.walk(directory_path): # files_in_dir to avoid conflict
            processed_files += len(files_in_dir)
        
        # 转换结果格式
        duplicate_groups = {}
        for level, groups_found in results.items(): # groups_found to avoid conflict
            for i, group in enumerate(groups_found):
                group_key = f"{level.value}_{i}_{group.score:.1f}" # 生成唯一的组key
                file_paths = [f.path for f in group.files]
                if len(file_paths) > 1:
                    duplicate_groups[group_key] = file_paths
                    
                    # 这部分日志现在主要由 finder 内部的 _log 和回调处理
                    # _local_log(f"找到{level.value}组:", "INFO")
                    # _local_log(f"  评分: {group.score:.1f}", "DETAIL")
                    # _local_log(f"  原因: {', '.join(set(group.reasons))}", "DETAIL")
                    # for file_meta in group.files:
                    #    _local_log(f"  - {file_meta.path}", "DETAIL")
        
        if not duplicate_groups:
            _local_log("未找到重复文件。", "INFO")
        else:
            _local_log(f"总共找到 {len(duplicate_groups)} 个不同等级的重复组。", "INFO")
            
    except InterruptedError:
        _local_log("扫描操作被用户中止。", "WARNING")
        return {}, logs, processed_files, skipped_unsupported, skipped_hash_errors
    except Exception as e:
        error_msg = f"扫描过程中出错 (增强版): {e}"
        _local_log(error_msg, "ERROR")
        skipped_hash_errors = 1 # 简化错误计数
    
    # 返回的logs现在更多是概要信息，详细信息通过回调
    return duplicate_groups, logs, processed_files, skipped_unsupported, skipped_hash_errors

def main():
    """主函数示例"""
    # 初始化查找器
    finder = EnhancedDuplicateFinder()
    
    # 测试目录
    test_dir = r"E:\test_duplicates_1"
    if os.path.exists(test_dir):
        results = finder.find_duplicates_in_directory(test_dir)
        finder.print_results(results)
    else:
        print(f"测试目录不存在: {test_dir}")

if __name__ == "__main__":
    main() 