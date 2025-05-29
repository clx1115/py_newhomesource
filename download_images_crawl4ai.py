import json
import os
import asyncio
from datetime import datetime
from crawl4ai import AsyncWebCrawler
import hashlib
from urllib.parse import urlparse
import logging
import aiohttp
import csv
from io import StringIO

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def escape_field(field):
    """转义字段中的特殊字符"""
    if not isinstance(field, str):
        field = str(field)
    return field.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')

def load_existing_downloads(mapping_file):
    """加载已下载的图片信息"""
    downloaded_urls = {}  # 改为字典，存储URL到本地路径的映射
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f, delimiter='\t')
                next(reader)  # 跳过表头
                for row in reader:
                    if len(row) >= 3:  # 确保至少有URL和本地路径字段
                        downloaded_urls[row[1]] = row[2]  # URL作为键，本地路径作为值
            logger.info(f"Found {len(downloaded_urls)} previously downloaded images")
        except Exception as e:
            logger.error(f"Error loading existing downloads: {str(e)}")
    return downloaded_urls

async def download_image(session, url, save_dir, property_info, mapping_file, downloaded_urls):
    """使用aiohttp下载单个图片并实时记录信息"""
    try:
        # 如果URL已经下载过，使用已存在的路径
        if url in downloaded_urls:
            logger.info(f"Skip already downloaded: {url}")
            relative_path = downloaded_urls[url]
            
            # # 准备记录信息，使用已存在的路径
            # record = [
            #     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # 下载时间
            #     escape_field(url),                              # 原始URL
            #     escape_field(relative_path),                    # 使用已存在的本地路径
            #     property_info.get('CommunityId', ''),          # 房源ID
            #     property_info.get('CommunityName', ''),        # 房源名称
            #     property_info.get('BuilderId', ''),            # 建筑商ID
            #     property_info.get('MarketId', ''),             # 市场ID
            #     property_info.get('MarketName', ''),           # 市场名称
            #     property_info.get('StateAbbr', ''),            # 州缩写
            #     property_info.get('City', ''),                 # 城市
            #     escape_field(property_info.get('address', '')),# 地址
            #     escape_field(property_info.get('price', '')),  # 价格
            #     escape_field(property_info.get('details', '')),# 详情
            #     escape_field(property_info.get('builder', '')) # 建筑商
            # ]
            
            # # 写入记录
            # with open(mapping_file, 'a', encoding='utf-8', newline='') as f:
            #     writer = csv.writer(f, delimiter='\t')
            #     writer.writerow(record)
            return True, relative_path  # 返回成功状态和相对路径

        # 获取文件扩展名
        parsed_url = urlparse(url)
        file_extension = os.path.splitext(parsed_url.path)[1]
        if not file_extension:
            file_extension = '.jpg'  # 默认扩展名

        # 使用link中的ID创建子目录
        link = property_info.get('link', '')
        property_id = link.split('/')[-1] if link and '/' in link else 'unknown'
        property_dir = os.path.join(save_dir, property_id)
        os.makedirs(property_dir, exist_ok=True)
        
        # 从URL中提取最后的数字作为文件名
        url_parts = url.split('/')
        image_id = next((part.split('-')[0] for part in reversed(url_parts) if part.split('-')[0].isdigit()), None)
        if image_id:
            filename = f"{image_id}{file_extension}"
        else:
            # 如果URL中没有数字，使用哈希作为备选
            url_hash = hashlib.md5(url.encode()).hexdigest()
            filename = f"{url_hash}{file_extension}"
        
        # 构建图片文件名和路径
        full_path = os.path.join(property_dir, filename)
        relative_path = os.path.relpath(full_path, save_dir)

        logger.info(f"Downloading: {url} -> {full_path} -> {relative_path} -> {os.path.exists(full_path)}")
        # 准备记录信息
        # record = [
        #     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # 下载时间
        #     escape_field(url),                              # 原始URL
        #     escape_field(relative_path),                    # 本地路径
        #     property_info.get('CommunityId', ''),          # 房源ID
        #     property_info.get('CommunityName', ''),        # 房源名称
        #     property_info.get('BuilderId', ''),            # 建筑商ID
        #     property_info.get('MarketId', ''),             # 市场ID
        #     property_info.get('MarketName', ''),           # 市场名称
        #     property_info.get('StateAbbr', ''),            # 州缩写
        #     property_info.get('City', ''),                 # 城市
        #     escape_field(property_info.get('address', '')),# 地址
        #     escape_field(property_info.get('price', '')),  # 价格
        #     escape_field(property_info.get('details', '')),# 详情
        #     escape_field(property_info.get('builder', '')) # 建筑商
        # ]
        
        # 如果文件已存在，只记录信息不下载
        if os.path.exists(full_path):
            logger.info(f"File already exists: {filename}")
            # 写入记录
            # with open(mapping_file, 'a', encoding='utf-8', newline='') as f:
            #     writer = csv.writer(f, delimiter='\t')
            #     writer.writerow(record)
            downloaded_urls[url] = full_path
            return True, full_path #relative_path
            
        # 设置headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.newhomesource.com/',
            'Origin': 'https://www.newhomesource.com'
        }
        
        # 使用aiohttp下载图片
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                # 读取图片内容并保存
                content = await response.read()
                with open(full_path, 'wb') as f:
                    f.write(content)
                logger.info(f"Successfully downloaded: {filename}")
                
                # 写入记录
                # with open(mapping_file, 'a', encoding='utf-8', newline='') as f:
                #     writer = csv.writer(f, delimiter='\t')
                #     writer.writerow(record)
                
                # 添加到已下载集合
                downloaded_urls[url] = full_path
                return True, full_path #relative_path
            else:
                logger.error(f"Failed to download {url}, status code: {response.status}")
                return False, None
            
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")
        return False, None

async def process_json_and_download_images():
    """处理JSON文件并下载所有图片"""
    try:
        # JSON文件路径
        json_file = "getHotDealProperties_output_Sacramento.json"
        
        # 确保JSON文件存在
        if not os.path.exists(json_file):
            logger.error(f"JSON file not found: {json_file}")
            return
        
        # 读取JSON文件
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建基础保存目录
        current_date = datetime.now()
        base_dir = os.path.dirname(json_file)
        save_dir = os.path.join(
            base_dir,
            'photo',
            str(current_date.year),
            str(current_date.month).zfill(2)
        )
        os.makedirs(save_dir, exist_ok=True)
        
        # 创建或加载映射文件
        mapping_file = os.path.join(save_dir, 'image_property_mapping.csv')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
        
        downloaded_urls = load_existing_downloads(mapping_file)
        
        # 如果是新文件，写入表头
        if not os.path.exists(mapping_file):
            headers = [
                'Download Time',
                'Original URL',
                'Local Path',
                'Community ID',
                'Community Name',
                'Builder ID',
                'Market ID',
                'Market Name',
                'State',
                'City',
                'Address',
                'Price',
                'Details',
                'Builder'
            ]
            with open(mapping_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(headers)
        
        # 创建aiohttp会话
        timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
        connector = aiohttp.TCPConnector(limit=30)  # 限制并发连接数
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            success_count = 0
            failed_urls = []
            total_images = 0
            
            # 处理每个房源
            for property_item in data:
                if 'images' in property_item and isinstance(property_item['images'], list):
                    # 过滤掉非图片URL
                    valid_urls = [url for url in property_item['images'] 
                                if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif'])]
                    total_images += len(valid_urls)
                    
                    # 为每个房源创建一个本地图片路径列表
                    local_image_paths = []
                    
                    # 下载该房源的所有图片
                    for url in valid_urls:
                        if url:  # 确保URL不为空
                            parsed_url = urlparse(url)
                            file_extension = os.path.splitext(parsed_url.path)[1]
                            if not file_extension:
                                file_extension = '.jpg'  # 默认扩展名
                                
                            # 获取文件名和路径
                            link = property_item.get('link', '')
                            property_id = link.split('/')[-1] if link and '/' in link else 'unknown'
                            property_dir = os.path.join(save_dir, property_id)
                            
                            # 从URL中提取最后的数字作为文件名
                            url_parts = url.split('/')
                            image_id = next((part.split('-')[0] for part in reversed(url_parts) if part.split('-')[0].isdigit()), None)
                            if image_id:
                                filename = f"{image_id}{file_extension}"
                            else:
                                url_hash = hashlib.md5(url.encode()).hexdigest()
                                filename = f"{url_hash}{file_extension}"
                                
                            full_path = os.path.join(property_dir, filename)
                            # 获取绝对路径
                            # abs_path = os.path.abspath(full_path)
                            
                            success, relative_path = await download_image(session, url, save_dir, property_item, mapping_file, downloaded_urls)
                            if success:
                                success_count += 1
                                # local_image_paths.append(abs_path)
                                local_image_paths.append(relative_path)
                            else:
                                failed_urls.append(url)
                            # 添加短暂延时避免请求过快
                            # await asyncio.sleep(0.1)
                    
                    # 将下载的图片路径保存到property_item中
                    property_item['local_image_paths'] = local_image_paths
            
            # 保存更新后的JSON文件
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 保存失败的URL到文件
            if failed_urls:
                failed_file = os.path.join(save_dir, 'failed_downloads.txt')
                with open(failed_file, 'w', encoding='utf-8') as f:
                    for url in failed_urls:
                        f.write(f"{url}\n")
                logger.warning(f"Failed URLs saved to: {failed_file}")
        
        logger.info(f"下载完成！成功下载 {success_count} 个图片，共 {total_images} 个图片")
        logger.info(f"发现的唯一图片总数: {total_images}")
        logger.info(f"之前已下载的图片数: {len(downloaded_urls)}")
        logger.info(f"图片映射保存到: {mapping_file}")
        logger.info(f"已更新JSON文件，添加了本地图片路径: {json_file}")
        if failed_urls:
            logger.warning(f"下载失败的图片数: {len(failed_urls)}")
        
    except Exception as e:
        logger.error(f"处理JSON文件时出错: {str(e)}")

def main():
    # 运行异步下载任务
    asyncio.run(process_json_and_download_images())

if __name__ == "__main__":
    main()
