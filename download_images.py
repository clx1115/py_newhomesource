import json
import os
import aiohttp
import asyncio
from datetime import datetime
import hashlib
from urllib.parse import urlparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def download_image(session, url, save_path):
    """下载单个图片的异步函数"""
    try:
        # 从URL生成唯一的文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()
        parsed_url = urlparse(url)
        file_extension = os.path.splitext(parsed_url.path)[1]
        if not file_extension:
            file_extension = '.jpg'  # 默认扩展名
        
        filename = f"{url_hash}{file_extension}"
        full_path = os.path.join(save_path, filename)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(full_path):
            logger.info(f"File already exists: {filename}")
            return
        
        async with session.get(url) as response:
            if response.status == 200:
                with open(full_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                logger.info(f"Successfully downloaded: {filename}")
            else:
                logger.error(f"Failed to download {url}, status code: {response.status}")
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")

async def process_json_and_download_images(json_file):
    """处理JSON文件并下载所有图片"""
    try:
        # 读取JSON文件
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建保存目录
        current_date = datetime.now()
        save_dir = os.path.join(
            os.path.dirname(json_file),
            str(current_date.year),
            str(current_date.month).zfill(2)
        )
        os.makedirs(save_dir, exist_ok=True)
        
        # 收集所有需要下载的图片URL
        image_urls = set()
        for item in data:
            if 'images' in item and isinstance(item['images'], list):
                image_urls.update(item['images'])
        
        logger.info(f"Found {len(image_urls)} unique images to download")
        
        # 创建异步会话并下载图片
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in image_urls:
                if url:  # 确保URL不为空
                    task = download_image(session, url, save_dir)
                    tasks.append(task)
            
            # 使用asyncio.gather并发下载图片
            await asyncio.gather(*tasks)
        
        logger.info("All downloads completed!")
        
    except Exception as e:
        logger.error(f"Error processing JSON file: {str(e)}")

def main():
    # JSON文件路径
    json_file = "getHotDealProperties_output_20250110.json"
    
    # 确保JSON文件存在
    if not os.path.exists(json_file):
        logger.error(f"JSON file not found: {json_file}")
        return
    
    # 运行异步下载任务
    asyncio.run(process_json_and_download_images(json_file))

if __name__ == "__main__":
    main()
