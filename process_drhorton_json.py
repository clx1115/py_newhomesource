import os
import json
import logging
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_beds_from_homeplans(homeplans):
    """从homeplans中提取beds值"""
    beds_values = []
    for plan in homeplans:
        if 'details' in plan and plan['details'].get('beds'):
            try:
                # 处理可能的格式："3 bd" 或 "3"
                beds_str = str(plan['details']['beds']).split()[0]  # 取第一个词，去掉可能的"bd"
                beds = int(beds_str)
                beds_values.append(beds)
            except (ValueError, TypeError, IndexError):
                continue
    return beds_values

def process_json_file(file_path):
    """处理单个JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 检查必要的字段是否存在
        if 'details' not in data:
            logger.warning(f"文件 {file_path} 缺少必要的字段")
            return
            
        # 获取所有有效的beds值（从homesites）
        beds_values = []
        if 'homesites' in data:
            for homesite in data['homesites']:
                if homesite.get('beds'):
                    try:
                        beds = int(str(homesite['beds']).split()[0])  # 处理可能的"3 bd"格式
                        beds_values.append(beds)
                    except (ValueError, TypeError, IndexError):
                        continue
        
        # 如果homesites中没有有效的beds值，尝试从homeplans获取
        if not beds_values and 'homeplans' in data:
            beds_values = get_beds_from_homeplans(data['homeplans'])
        
        if not beds_values:
            logger.warning(f"文件 {file_path} 在homesites和homeplans中都没有有效的beds值")
            return
            
        # 计算最小值和最大值
        min_beds = min(beds_values)
        max_beds = max(beds_values)
        
        # 更新bed_range
        if min_beds == max_beds:
            data['details']['bed_range'] = f"{max_beds}"
        else:
            data['details']['bed_range'] = f"{min_beds} - {max_beds}"
            
        # 保存更新后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"成功更新文件 {file_path}, bed_range: {data['details']['bed_range']}")
        
    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出错: {str(e)}")

def main():
    """主函数"""
    try:
        # 指定数据目录
        data_dir = 'data/drhorton'
        
        # 确保目录存在
        if not os.path.exists(data_dir):
            logger.error(f"目录 {data_dir} 不存在")
            return
            
        # 获取所有JSON文件
        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') 
                     and f not in ['everbe.json', 'florida_links.json']]
        
        if not json_files:
            logger.warning(f"在 {data_dir} 中没有找到需要处理的JSON文件")
            return
            
        # 处理每个文件
        for json_file in json_files:
            file_path = os.path.join(data_dir, json_file)
            process_json_file(file_path)
            
        logger.info(f"成功处理了 {len(json_files)} 个文件")
        
    except Exception as e:
        logger.error(f"处理过程中出错: {str(e)}")

if __name__ == "__main__":
    main() 