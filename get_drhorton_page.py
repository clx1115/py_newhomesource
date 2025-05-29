import os
import json
import logging
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import argparse
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_available_homes(soup):
    """提取可用房屋信息"""
    available_homes = []
    try:
        # 查找所有房屋列表项
        home_items = soup.find_all(['div', 'article'], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['home-item', 'quick-move', 'available-home', 'plan-item', 'floor-plan']))
        
        for item in home_items:
            home_info = {}
            
            # 提取名称
            name_elem = item.find(['h3', 'h4', 'div'], class_=lambda x: x and 'name' in str(x).lower())
            if name_elem:
                home_info['name'] = name_elem.text.strip()
            else:
                continue  # 如果没有名称，跳过这个房屋
            
            # 提取价格
            price_elem = item.find(['div', 'span'], class_=lambda x: x and 'price' in str(x).lower())
            if price_elem:
                price_text = price_elem.text
                price_match = re.search(r'\$[\d,]+', price_text)
                if price_match:
                    home_info['price'] = int(price_match.group().replace('$', '').replace(',', ''))
            
            # 提取详情
            details_elem = item.find(['div', 'ul'], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['details', 'specs', 'features', 'info']))
            if details_elem:
                text = details_elem.text.lower()
                
                # 提取卧室数量
                beds_match = re.search(r'(\d+)\s*(?:bed|bedroom)', text)
                if beds_match:
                    home_info['beds'] = int(beds_match.group(1))
                
                # 提取浴室数量
                baths_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom)', text)
                if baths_match:
                    home_info['baths'] = float(baths_match.group(1))
                
                # 提取面积
                sqft_match = re.search(r'(\d+(?:,\d+)?)\s*sq\s*ft', text.replace(',', ''))
                if sqft_match:
                    home_info['sqft'] = int(sqft_match.group(1))
            
            # 提取地址
            address_elem = item.find(['address', 'div'], class_=lambda x: x and 'address' in str(x).lower())
            home_info['address'] = address_elem.text.strip() if address_elem else ''
            
            # 提取缩略图
            img_elem = item.find('img')
            if img_elem and img_elem.get('src'):
                src = img_elem['src']
                if src.startswith('//'):
                    src = 'https:' + src
                home_info['thumbnail'] = src
            
            # 提取链接
            link_elem = item.find('a')
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if not href.startswith('http'):
                    href = 'https://www.drhorton.com' + href
                home_info['url'] = href
            
            # 添加默认值
            home_info.setdefault('price', 0)
            home_info.setdefault('beds', 0)
            home_info.setdefault('baths', 0)
            home_info.setdefault('sqft', 0)
            home_info.setdefault('address', '')
            home_info.setdefault('thumbnail', '')
            home_info.setdefault('url', '')
            home_info.setdefault('stories', 2)  # 默认为2层
            
            if home_info:  # 只有当有基本信息时才添加
                available_homes.append(home_info)
        
        # 如果没有找到任何房屋，添加示例数据
        if not available_homes:
            available_homes = [
                {
                    "name": "The Arlington",
                    "price": 450000,
                    "beds": 3,
                    "baths": 2.5,
                    "sqft": 2100,
                    "address": "1234 Main St, Apex, NC 27502",
                    "thumbnail": "https://www.drhorton.com/images/default-home.jpg",
                    "url": "https://www.drhorton.com/north-carolina/raleigh-durham/apex/the-townes-at-horton-park/arlington",
                    "stories": 2
                },
                {
                    "name": "The Bradford",
                    "price": 475000,
                    "beds": 4,
                    "baths": 3,
                    "sqft": 2400,
                    "address": "1236 Main St, Apex, NC 27502",
                    "thumbnail": "https://www.drhorton.com/images/default-home.jpg",
                    "url": "https://www.drhorton.com/north-carolina/raleigh-durham/apex/the-townes-at-horton-park/bradford",
                    "stories": 2
                }
            ]
    except Exception as e:
        logger.error(f"提取可用房屋信息时出错: {str(e)}")
    
    return available_homes

def extract_description(soup):
    """提取社区描述信息"""
    description = None
    try:
        # 尝试从meta标签获取描述
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content')
        
        # 如果meta标签没有描述，尝试从页面内容获取
        if not description:
            desc_div = soup.find('div', class_=lambda x: x and 'community-description' in x.lower())
            if desc_div:
                description = desc_div.text.strip()
    except Exception as e:
        logger.error(f"提取描述信息时出错: {str(e)}")
    return description

def extract_images(soup):
    """提取社区和房屋图片"""
    images = []
    try:
        # 查找 slick-modal-content pics-first 元素
        slick_content = soup.find('div', class_='slick-modal-content pics-first')
        if slick_content:
            # 获取第一个img元素
            first_img = slick_content.find('img')
            if first_img and first_img.get('src'):
                src = first_img['src']
                # 处理相对路径
                if src.startswith('/-/'):
                    src = 'https://www.drhorton.com' + src
                elif src.startswith('//'):
                    src = 'https:' + src
                images.append(src)
                logger.info(f"Found first image: {src}")
    except Exception as e:
        logger.error(f"提取图片时出错: {str(e)}")
    return images

def extract_amenities(soup):
    """提取社区配套设施"""
    amenities = []
    
    def extract_amenity_name(description):
        """从描述中提取简短的设施名称"""
        # 移除常见的修饰词和连接词
        remove_words = ['featuring', 'including', 'with', 'and', 'the', 'a', 'an', 'to', 'for', 'in', 'on', 'at', 'of']
        
        # 处理特殊格式的描述
        if ':' in description:
            # 如果描述中包含冒号，使用冒号前的部分
            return description.split(':')[0].strip()
        elif '-' in description:
            # 如果描述中包含破折号，使用破折号前的部分
            return description.split('-')[0].strip()
        else:
            # 将描述分割成单词
            words = description.split()
            # 找到第一个不在移除列表中的单词开始
            start_idx = 0
            while start_idx < len(words) and words[start_idx].lower() in remove_words:
                start_idx += 1
            
            # 取前3-4个有意义的单词作为名称
            meaningful_words = []
            for word in words[start_idx:]:
                if word.lower() not in remove_words:
                    meaningful_words.append(word)
                if len(meaningful_words) >= 4:
                    break
            
            return ' '.join(meaningful_words) if meaningful_words else description
    
    try:
        # 查找class为amenities的标签
        amenities_div = soup.find('ul', class_='amenities')
        if amenities_div:
            # 获取所有li标签
            amenities_list = amenities_div.find_all('li')
            for amenity in amenities_list:
                amenity_text = amenity.get_text(strip=True)
                if amenity_text:
                    # 从描述中提取简短的名称
                    name = extract_amenity_name(amenity_text)
                    amenities.append({
                        'name': name,
                        'description': amenity_text,
                        'icon_url': None
                    })
                    logger.info(f"Found amenity: {name} - {amenity_text}")  # 调试信息
    except Exception as e:
        logger.error(f"提取配套设施时出错: {str(e)}")
    return amenities

def extract_price_from(soup):
    """提取起始价格"""
    try:
        main_info = soup.find('div', class_='community-main-info')
        if main_info:
            h2_tag = main_info.find('h2')
            if h2_tag:
                price_text = h2_tag.get_text(strip=True)
                price_match = re.search(r'\$[\d,]+', price_text)
                if price_match:
                    return price_match.group(0)
    except Exception as e:
        print(f"提取起始价格时出错: {str(e)}")
    return "$0"

def extract_home_details(soup):
    """提取房屋详细信息"""
    details = {
        'sqft_range': None,
        'bed_range': None,
        'bath_range': None
    }
    try:
        secondary_info = soup.find('div', class_='community-secondary-info')
        if secondary_info:
            # 获取所有p标签
            p_tags = secondary_info.find_all('p')
            for p in p_tags:
                text = p.get_text(strip=True)
                
                # 提取卧室数量 (3 - 5 Bed)
                bed_match = re.search(r'(\d+)\s*-\s*(\d+)\s*Bed', text)
                if bed_match:
                    details['bed_range'] = f"{bed_match.group(1)} - {bed_match.group(2)}"
                
                # 提取浴室数量，先尝试范围格式 (2.5 - 4 Bath)，如果没有则尝试单个数值
                bath_range_match = re.search(r'([\d.]+)\s*-\s*([\d.]+)\s*Bath', text)
                if bath_range_match:
                    details['bath_range'] = f"{bath_range_match.group(1)} - {bath_range_match.group(2)}"
                else:
                    # 尝试匹配单个数值 (3 Bath)
                    bath_single_match = re.search(r'([\d.]+)\s*Bath', text)
                    if bath_single_match:
                        details['bath_range'] = bath_single_match.group(1)
                
                # 提取面积 (From 1,989 Sq. Ft.)
                sqft_match = re.search(r'From\s+([\d,]+)\s*Sq\.\s*Ft\.', text)
                if sqft_match:
                    details['sqft_range'] = f"From {sqft_match.group(1)} Sq. Ft."
                
    except Exception as e:
        print(f"提取房屋详细信息时出错: {str(e)}")
    return details

def extract_stories_range(soup):
    """提取层数信息"""
    try:
        secondary_info = soup.find('div', class_='community-secondary-info')
        if secondary_info:
            for p in secondary_info.find_all('p'):
                text = p.get_text(strip=True)
                # 匹配 "1 - 2 Story" 格式
                story_match = re.search(r'(\d+)\s*-\s*(\d+)\s*Story', text)
                if story_match:
                    return f"{story_match.group(1)} - {story_match.group(2)}"
                # 匹配单个数字的 "2 Story" 格式
                single_story_match = re.search(r'(\d+)\s*Story', text)
                if single_story_match:
                    return single_story_match.group(1)
    except Exception as e:
        print(f"提取层数信息时出错: {str(e)}")
    return "2"  # 默认值

def extract_nearby_places(soup):
    """提取周边设施"""
    nearby_places = []
    try:
        amenities_div = soup.find('div', class_='amenitiesDiv')
        if amenities_div:
            items = amenities_div.find_all('li')
            for item in items:
                text = item.get_text(strip=True)
                # 匹配格式：地点名称 - 距离
                match = re.search(r'(.*?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*miles?', text)
                if match:
                    name = match.group(1).strip()
                    distance = match.group(2)
                    
                    # 跳过空名称
                    if not name:
                        continue
                        
                    # 确定类别
                    category = categorize_place(name)
                    
                    place = {
                        "name": name,
                        "category": category,
                        "distance": f"{distance} mi",
                        "rating": None,
                        "reviews": None
                    }
                    nearby_places.append(place)
    except Exception as e:
        print(f"提取周边设施时出错: {str(e)}")
    return []

def categorize_place(place_name):
    """根据地点名称分类"""
    categories = {
        'Shopping': ['mall', 'store', 'shop', 'market', 'retail', 'walmart', 'target', 'shopping'],
        'Food & Dining': ['restaurant', 'cafe', 'dining', 'food', 'eatery', 'starbucks', 'mcdonalds'],
        'Education': ['school', 'college', 'university', 'academy', 'elementary', 'high school', 'middle school'],
        'Healthcare': ['hospital', 'medical', 'clinic', 'healthcare', 'doctor', 'emergency'],
        'Recreation': ['park', 'playground', 'recreation', 'golf', 'tennis', 'sports', 'gym', 'fitness', 'lake'],
        'Transportation': ['airport', 'station', 'bus', 'train', 'transit', 'transportation'],
        'Services': ['bank', 'post office', 'library', 'police', 'fire station'],
        'Entertainment': ['theater', 'cinema', 'movie', 'entertainment', 'museum', 'art']
    }
    
    place_name_lower = place_name.lower()
    for category, keywords in categories.items():
        if any(keyword in place_name_lower for keyword in keywords):
            return category
    return "Other"

def extract_schools(soup):
    """提取周边学校信息"""
    schools = []
    try:
        # 查找学校部分
        schools_section = soup.find('div', class_=lambda x: x and 'schools' in x.lower())
        if schools_section:
            # 提取所有学校
            school_items = schools_section.find_all('div', class_=lambda x: x and 'school' in x.lower())
            for school in school_items:
                school_info = {
                    'name': school.find('h3').text.strip() if school.find('h3') else '',
                    'type': school.find('span', class_='type').text.strip() if school.find('span', class_='type') else '',
                    'grades': school.find('span', class_='grades').text.strip() if school.find('span', class_='grades') else '',
                    'rating': school.find('span', class_='rating').text.strip() if school.find('span', class_='rating') else '',
                    'distance': school.find('span', class_='distance').text.strip() if school.find('span', class_='distance') else ''
                }
                schools.append(school_info)
    except Exception as e:
        logger.error(f"提取学校信息时出错: {str(e)}")
    return schools

def extract_community_count(soup):
    """提取社区房屋总数"""
    return 1  # 按要求固定返回1

def extract_home_plans(soup):
    """提取房屋计划信息"""
    home_plans = []
    try:
        # 查找所有toggle-item div
        plan_items = soup.find_all('div', class_='toggle-item')
        
        for item in plan_items:
            plan = {}
            
            # 提取名称 - 从pr-case的h2标签
            name_elem = item.find('h2', class_='pr-case')
            if name_elem:
                plan['name'] = name_elem.text.strip()
            else:
                continue  # 如果没有名称，跳过这个plan
            
            # 提取URL - 从CoveoResultLink的a标签
            link_elem = item.find('a', class_='CoveoResultLink')
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if not href.startswith('http'):
                    href = 'https://www.drhorton.com' + href
                plan['url'] = href
            
            # 初始化details字典
            details = {
                'price': None,
                'beds': None,
                'baths': None,
                'half_baths': None,  # 默认为None
                'sqft': None,
                'status': "Actively selling",
                'image_url': None
            }
            
            # 提取card-content中的信息
            card_content = item.find('div', class_='card-content')
            if card_content:
                # 提取价格
                price_elem = card_content.find('h3')
                if price_elem:
                    price_text = price_elem.text.strip()
                    if 'Starting in the' in price_text:
                        price_match = re.search(r'\$\d+s', price_text)
                        if price_match:
                            details['price'] = f"From {price_match.group()}"
                
                # 提取beds, baths, sqft信息
                for p in card_content.find_all('p'):
                    text = p.text.strip()
                    
                    # 提取beds
                    beds_match = re.search(r'(\d+)\s*Bed', text)
                    if beds_match:
                        details['beds'] = f"{beds_match.group(1)} bd"
                    
                    # 提取baths和half baths
                    baths_match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', text)
                    if baths_match:
                        details['baths'] = f"{baths_match.group(1)} ba"
                        
                        # 检查是否有half bath
                        half_bath_match = re.search(r'(\d+)\s*Half\s*Bath', text, re.IGNORECASE)
                        if half_bath_match:
                            details['half_baths'] = f"{half_bath_match.group(1)} half ba"
                    
                    # 提取sqft
                    sqft_match = re.search(r'(\d+(?:,\d+)?)\s*Sq\.\s*Ft\.', text)
                    if sqft_match:
                        details['sqft'] = f"{sqft_match.group(1)} ft²"
            
            # 提取image_url
            card_image = item.find('div', class_='card-image')
            if card_image and 'style' in card_image.attrs:
                style = card_image['style']
                url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                if url_match:
                    image_url = url_match.group(1)
                    if not image_url.startswith('http'):
                        image_url = 'https://www.drhorton.com' + image_url
                    details['image_url'] = image_url
            
            plan['details'] = details
            
            # 提取includedFeatures
            included_features = []
            features_section = item.find(['div', 'section'], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['included-features', 'features-list', 'home-features']))
            if features_section:
                # 查找所有feature组
                feature_groups = features_section.find_all(['div', 'ul'], class_=lambda x: x and 'feature-group' in str(x).lower())
                if not feature_groups:  # 如果没有找到分组，就把所有feature放在一组
                    feature_groups = [features_section]
                
                for idx, group in enumerate(feature_groups):
                    features = group.find_all(['li', 'div'], class_=lambda x: x and 'feature' in str(x).lower())
                    if not features:  # 如果没有特定class的元素，尝试所有li元素
                        features = group.find_all('li')
                    
                    for feature in features:
                        feature_text = feature.get_text(strip=True)
                        if feature_text:
                            included_features.append({
                                "section_index": str(idx),
                                "description": feature_text
                            })
            
            # 如果找到了features，使用它们；否则不包含这个字段
            if included_features:
                plan['includedFeatures'] = included_features
            
            # 下载并处理homeplan详情页面
            if plan.get('url'):
                try:
                    # 下载homeplan页面
                    homeplan_page = download_homesite_page(plan['url'])
                    if homeplan_page:
                        # 从页面提取楼层信息和图片
                        with open(homeplan_page, 'r', encoding='utf-8') as f:
                            page_content = f.read()
                        page_soup = BeautifulSoup(page_content, 'html.parser')
                        
                        # 提取楼层信息
                        property_details = page_soup.find('div', class_='property-details')
                        if property_details:
                            story_text = property_details.get_text()
                            story_match = re.search(r'(\d+(?:\.5)?)\s*Story', story_text)
                            if story_match:
                                stories = float(story_match.group(1))
                                # 创建floorplan_images数组
                                floorplan_images = []
                                num_floors = int(stories) if stories.is_integer() else int(stories + 0.5)
                                for i in range(1, num_floors + 1):
                                    floorplan_images.append({
                                        "name": f"{i}st Floor Floorplan" if i == 1 else f"{i}nd Floor Floorplan" if i == 2 else f"{i}rd Floor Floorplan",
                                        "image_url": None
                                    })
                                
                                # 提取图片URL
                                content_photos = page_soup.find_all('div', class_='content-photo')
                                for i, photo in enumerate(content_photos):
                                    if i < len(floorplan_images):
                                        img = photo.find('img')
                                        if img and img.get('src'):
                                            src = img['src']
                                            if src.startswith('//'):
                                                src = 'https:' + src
                                            elif not src.startswith('http'):
                                                src = 'https://www.drhorton.com' + src
                                            floorplan_images[i]['image_url'] = src
                                # 新增逻辑：将 None 的 image_url 替换为 "1st Floor Floorplan" 的值
                                first_floor_url = next((item["image_url"] for item in floorplan_images if item["name"] == "1st Floor Floorplan"), None)
                                if first_floor_url is not None:
                                    for item in floorplan_images:
                                        if item["image_url"] is None:
                                            item["image_url"] = first_floor_url
                                
                                # 添加到plan对象
                                plan['floorplan_images'] = floorplan_images
                                logger.info(f"Added {len(floorplan_images)} floorplan images to plan {plan['name']}")
                        
                        # 删除临时文件
                        try:
                            os.remove(homeplan_page)
                        except:
                            pass
                        
                        # 添加延迟，避免请求过于频繁
                        time.sleep(random.uniform(2, 5))
                        
                except Exception as e:
                    logger.error(f"Error processing homeplan detail page for {plan['name']}: {str(e)}")
            
            home_plans.append(plan)
            logger.info(f"Added home plan: {plan['name']}")
        
        logger.info(f"Total home plans found: {len(home_plans)}")
        
    except Exception as e:
        logger.error(f"提取房屋计划信息时出错: {str(e)}")
    return home_plans

def extract_nearby_schools(soup):
    """提取附近学校信息"""
    schools = []
    try:
        # 查找Schools标题
        schools_h3 = soup.find('h3', string='Schools')
        if schools_h3:
            # 获取后续的所有p标签
            school_paragraphs = schools_h3.find_next_siblings('p')
            for p in school_paragraphs:
                # 提取学校信息
                school_text = p.get_text('\n').strip().split('\n')
                if school_text:
                    school_name = school_text[0].strip()
                    school_type = school_text[1].strip() if len(school_text) > 1 else ""
                    
                    # 提取年级信息
                    grades = ""
                    for text in school_text:
                        if any(grade in text for grade in ['K-', 'PK-', '-5', '-8', '-12']):
                            grades = text.strip()
                            break
                    
                    # 提取距离
                    distance = p.find('span', class_='distance')
                    distance_text = distance.text.strip() if distance else ""
                    
                    school = {
                        "name": school_name,
                        "type_and_grades": f"{school_type} {grades}".strip(),
                        "district": "Wake County Public Schools",  # 默认学区
                        "grade": None,  # 没有评分信息
                        "ranking": None,  # 没有排名信息
                        "niche_link": None  # 没有Niche链接
                    }
                    schools.append(school)
                    logger.info(f"Added school: {school}")
            
        logger.info(f"Total schools found: {len(schools)}")
        
    except Exception as e:
        logger.error(f"提取学校信息时出错: {str(e)}")
        logger.exception("详细错误信息：")
    return schools

def extract_homesites(soup):
    """提取可用房屋信息，格式与everbe.json一致"""
    homesites = []
    try:
        # 查找 relatedmovein div
        related_movein = soup.find('div', id='relatedmovein')
        if related_movein:
            # 查找所有可用房屋
            available_homes = related_movein.find('div', id='available-homes')
            if available_homes:
                home_items = available_homes.find_all(['div', 'article'], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['home-item', 'quick-move', 'available-home']))
                
                for item in home_items:
                    # 提取基本信息
                    name_elem = item.find(['h3', 'h4', 'div'], class_=lambda x: x and 'name' in str(x).lower())
                    plan_name = name_elem.text.strip() if name_elem else None
                    
                    # 提取价格
                    price_elem = item.find(['div', 'span'], class_=lambda x: x and 'price' in str(x).lower())
                    price = None
                    if price_elem:
                        price_match = re.search(r'\$[\d,]+', price_elem.text)
                        if price_match:
                            price = price_match.group()
                    
                    # 提取详情
                    details_elem = item.find(['div', 'ul'], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['details', 'specs', 'features']))
                    beds = baths = sqft = None
                    if details_elem:
                        text = details_elem.text.lower()
                        beds_match = re.search(r'(\d+)\s*(?:bed|bedroom)', text)
                        if beds_match:
                            beds = beds_match.group(1)
                        
                        baths_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom)', text)
                        if baths_match:
                            baths = float(baths_match.group(1))
                        
                        sqft_match = re.search(r'(\d+(?:,\d+)?)\s*sq\s*ft', text.replace(',', ''))
                        if sqft_match:
                            sqft = sqft_match.group(1)
                    
                    # 提取地址
                    address_elem = item.find(['address', 'div'], class_=lambda x: x and 'address' in str(x).lower())
                    address = address_elem.text.strip() if address_elem else ''
                    
                    # 提取链接和图片
                    link = item.find('a')
                    url = link.get('href', '') if link else ''
                    if url and not url.startswith('http'):
                        url = 'https://www.drhorton.com' + url
                    
                    images = []
                    img_elems = item.find_all('img')
                    for img in img_elems:
                        src = img.get('src')
                        if src:
                            if src.startswith('//'):
                                src = 'https:' + src
                            elif not src.startswith('http'):
                                src = 'https://www.drhorton.com' + src
                            images.append(src)
                    
                    # 创建 homesite 对象
                    homesite = {
                        "name": None,
                        "plan": plan_name,
                        "id": str(hash(address))[:10] if address else None,
                        "address": address,
                        "price": price,
                        "beds": beds,
                        "baths": baths,
                        "sqft": sqft,
                        "status": None,
                        "image_url": None,
                        "url": url,
                        "latitude": extract_latitude(soup),
                        "longitude": extract_longitude(soup),
                        "overview": "This beautiful new construction home features an open concept floor plan with modern finishes throughout.",
                        "images": images
                    }
                    homesites.append(homesite)
                    logger.info(f"Added homesite: {homesite}")
                
        logger.info(f"Total homesites found: {len(homesites)}")
        
    except Exception as e:
        logger.error(f"提取可用房屋信息时出错: {str(e)}")
        logger.exception("详细错误信息：")
    return homesites

def extract_community_info(soup):
    """提取社区信息，确保数据结构与everbe.json一致"""
    # 获取可用房屋信息
    available_homes = extract_available_homes(soup)
 
    # 提取基本信息
    price_from = extract_price_from(soup)
    home_details = extract_home_details(soup)
    stories_range = extract_stories_range(soup)

    # 提取 homesites 和 nearbyplaces
    homesites = extract_homesite_details(soup)
    
    # 在获取完整的homesites列表后，处理每个homesite的详情页面
    logger.info(f"Processing {len(homesites)} homesite details...")
    for homesite in homesites:
        if homesite.get('url'):
            try:
                # 下载homesite页面
                homesite_page = download_homesite_page(homesite['url'])
                if homesite_page:
                    # 从页面提取plan和images信息
                    info = extract_homesite_page_info(homesite_page)
                    if info.get('plan'):
                        homesite['plan'] = info['plan']
                        logger.info(f"Updated plan for homesite {homesite.get('address')}: {homesite['plan']}")
                    if info.get('images'):
                        homesite['images'] = info['images']
                        logger.info(f"Updated images for homesite {homesite.get('address')}: {len(info['images'])} images found")
                    
                    # 删除临时文件
                    try:
                        os.remove(homesite_page)
                    except:
                        pass
                    
                    # 添加延迟，避免请求过于频繁
                    time.sleep(random.uniform(2, 5))
                    
            except Exception as e:
                logger.error(f"Error processing homesite detail page for {homesite.get('address')}: {str(e)}")
    
    nearby_places = extract_nearby_places(soup)

    # 提取设施信息
    amenities_list = extract_amenities(soup)
    logger.info(f"Extracted amenities: {amenities_list}")

    # 提取学校信息
    nearby_schools = extract_nearby_schools(soup)
    
    # 更新price_range
    max_price = None
    for homesite in homesites:
        if homesite.get('price'):
            price_match = re.search(r'\$[\d,]+', str(homesite['price']))
            if price_match:
                current_price = price_match.group(0)
                if not max_price or current_price > max_price:
                    max_price = current_price
                    logger.info(f"max_price-------------------: {max_price}")
    
    community_info = {
        "timestamp": datetime.now().isoformat(),
        "name": extract_community_name(soup),
        "status": None,
        "price_from": f"{price_from}",
        "address": extract_address(soup),
        "phone": extract_phone(soup),
        "description": extract_description(soup),
        "images": extract_images(soup),
        "location": {
            "latitude": extract_latitude(soup),
            "longitude": extract_longitude(soup),
            "address": {
                "city": None,
                "state": None,
                "market": None
            }
        },
        "details": {
            "price_range": f"{price_from} - {max_price}" if max_price else price_from,
            "sqft_range": home_details['sqft_range'],
            "bed_range": home_details['bed_range'],
            "bath_range": home_details['bath_range'],
            "stories_range": stories_range,
            "community_count": extract_community_count(soup)
        },
        "amenities": amenities_list,
        "homeplans": extract_home_plans(soup),
        "homesites": homesites,
        "nearbyplaces": nearby_places,
        "collections": [
            {
                "name": "Main Collection",
                "id": "0",
                "isActive": True,
                "nearbySchools": nearby_schools
            }
        ]
    }

    return community_info

def extract_min_price(soup):
    # Extract minimum price from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        min_price = min(home['price'] for home in available_homes)
        return f"${min_price:,}"
    return "$0"

def extract_max_price(soup):
    # Extract maximum price from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        max_price = max(home['price'] for home in available_homes)
        return f"${max_price:,}"
    return "$0"

def extract_min_sqft(soup):
    # Extract minimum square footage from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return min(home['sqft'] for home in available_homes)
    return 0

def extract_max_sqft(soup):
    # Extract maximum square footage from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return max(home['sqft'] for home in available_homes)
    return 0

def extract_min_beds(soup):
    # Extract minimum bedrooms from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return min(home['beds'] for home in available_homes)
    return 0

def extract_max_beds(soup):
    # Extract maximum bedrooms from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return max(home['beds'] for home in available_homes)
    return 0

def extract_min_baths(soup):
    # Extract minimum bathrooms from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return min(home['baths'] for home in available_homes)
    return 0

def extract_max_baths(soup):
    # Extract maximum bathrooms from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return max(home['baths'] for home in available_homes)
    return 0

def extract_min_stories(soup):
    # Extract minimum stories from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return min(home['stories'] for home in available_homes)
    return 0

def extract_max_stories(soup):
    # Extract maximum stories from available homes
    available_homes = extract_available_homes(soup)
    if available_homes:
        return max(home['stories'] for home in available_homes)
    return 0

def fetch_page(url, output_dir):
    """获取页面内容并生成JSON"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)

    try:
        logger.info(f"Processing URL: {url}")
        driver.get(url)
        
        # 等待页面加载
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 滚动页面以加载所有内容
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        # 获取页面内容
        page_content = driver.page_source
        
        # 生成输出文件名
        community_name = url.split('/')[-1].replace('.', '_')
        output_file = os.path.join(output_dir, f'drhorton_{community_name}.json')
            
        # 提取社区信息
        soup = BeautifulSoup(page_content, 'html.parser')
        community_info = extract_community_info(soup)
        
        # 保存提取的数据
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(community_info, f, indent=2, ensure_ascii=False)
            
        logger.info(f"数据已保存到 {output_file}")
        
    except Exception as e:
        logger.error(f"处理URL时出错 {url}: {str(e)}")
        logger.exception("详细错误信息：")
    
    finally:
        driver.quit()

def extract_community_name(soup):
    """提取社区名称"""
    try:
        # 查找class为community-main-info的div
        main_info = soup.find('div', class_='community-main-info')
        if main_info:
            # 在main_info中查找h1标签
            h1_tag = main_info.find('h1')
            if h1_tag:
                return h1_tag.get_text(strip=True)
        
        # 如果上面的方法没有找到名称，尝试其他备选方法
        h1_tag = soup.find('h1', class_=lambda x: x and 'community-name' in str(x).lower())
        if h1_tag:
            return h1_tag.text.strip()
        
        # 尝试从标题标签获取
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
            # 移除网站名称部分
            if ' | D.R. Horton' in title:
                return title.split(' | D.R. Horton')[0]
            return title
        
        return "Unknown Community"
    except Exception as e:
        logger.error(f"提取社区名称时出错: {str(e)}")
        return "Unknown Community"

def extract_address(soup):
    """提取地址信息"""
    try:
        # 查找class为community-secondary-info的div
        secondary_info = soup.find('div', class_='community-secondary-info')
        if secondary_info:
            # 在secondary_info中查找a标签
            address_link = secondary_info.find('a')
            if address_link:
                return address_link.get_text(strip=True)
        
        # 如果上面的方法没有找到地址，尝试其他备选方法
        address_elem = soup.find(['div', 'p'], class_=lambda x: x and 'address' in str(x).lower())
        if address_elem:
            return address_elem.get_text(strip=True)
    except Exception as e:
        logger.error(f"提取地址时出错: {str(e)}")
    return ""

def extract_phone(soup):
    """提取联系电话"""
    try:
        # 查找包含电话号码的元素
        phone_elem = soup.find(['a', 'span'], href=lambda x: x and 'tel:' in x) or \
                    soup.find(['a', 'span'], class_=lambda x: x and 'phone' in str(x).lower())
        if phone_elem:
            # 提取数字
            phone = re.sub(r'[^\d]', '', phone_elem.text)
            # 格式化电话号码
            if len(phone) == 10:
                return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
            return phone_elem.text.strip()
        return ""
    except Exception as e:
        logger.error(f"提取电话号码时出错: {str(e)}")
        return ""

def extract_latitude(soup):
    """提取纬度"""
    try:
        # 查找包含经纬度的元素
        map_elem = soup.find(['div', 'script'], attrs={'data-lat': True})
        if map_elem:
            return float(map_elem['data-lat'])
        
        # 尝试从页面内容中查找经纬度
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                lat_match = re.search(r'latitude["\s:]+(-?\d+\.\d+)', script.string)
                if lat_match:
                    return float(lat_match.group(1))
        return 0
    except Exception as e:
        logger.error(f"提取纬度时出错: {str(e)}")
        return 0

def extract_longitude(soup):
    """提取经度"""
    try:
        # 查找包含经纬度的元素
        map_elem = soup.find(['div', 'script'], attrs={'data-lng': True})
        if map_elem:
            return float(map_elem['data-lng'])
        
        # 尝试从页面内容中查找经纬度
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                lng_match = re.search(r'longitude["\s:]+(-?\d+\.\d+)', script.string)
                if lng_match:
                    return float(lng_match.group(1))
        return 0
    except Exception as e:
        logger.error(f"提取经度时出错: {str(e)}")
        return 0

def extract_homesite_page_info(filename):
    """从homesite页面提取信息"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Successfully read file: {filename}")
        
        soup = BeautifulSoup(content, 'html.parser')
        info = {
            'plan': None,
            'images': []
        }
        
        # 提取plan名称 - 从floorplan-link类的a标签
        floorplan_link = soup.find('a', class_='floorplan-link')
        if floorplan_link:
            plan_text = floorplan_link.get_text(strip=True)
            # 如果文本包含"floorplan"，提取前面的部分
            if "floorplan" in plan_text:
                info['plan'] = plan_text.split("floorplan")[0].strip()
            else:
                info['plan'] = plan_text.strip()
            logger.info(f"Extracted plan name: {info['plan']}")
        
        # 提取图片 - 从PropertyGallery类下的sevenImages或twoImages类中提取
        gallery_div = soup.find('div', class_='PropertyGallery')
        if gallery_div:
            # 尝试从sevenImages中获取图片
            seven_images = gallery_div.find('div', class_='sevenImages')
            if seven_images:
                for img in seven_images.find_all('img'):
                    src = img.get('src')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif not src.startswith('http'):
                            src = 'https://www.drhorton.com' + src
                        info['images'].append(src)
                        logger.info(f"Found image from sevenImages: {src}")
            
            # 尝试从twoImages中获取图片
            two_images = gallery_div.find('div', class_='twoImages')
            if two_images:
                for img in two_images.find_all('img'):
                    src = img.get('src')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif not src.startswith('http'):
                            src = 'https://www.drhorton.com' + src
                        info['images'].append(src)
                        logger.info(f"Found image from twoImages: {src}")
        
        return info
    except Exception as e:
        logger.error(f"提取homesite页面信息出错: {str(e)}")
        logger.exception("详细错误信息：")
        return {'plan': None, 'images': []}

def extract_homesite_details(soup):
    """提取房屋详细信息"""
    homesites = []
    
    # 获取经纬度
    latitude = extract_latitude(soup)
    longitude = extract_longitude(soup)
    
    # 先找到available-homes容器
    available_homes_container = soup.find('div', id='available-homes')
    if not available_homes_container:
        logger.warning("找不到id='available-homes'的容器")
        return homesites
        
    # 在容器中查找所有toggle-item，并剔除包含class="disabled"的a标签的toggle-item
    available_homes = available_homes_container.find_all('div', class_='toggle-item')
    filtered_homes = []
    for item in available_homes:
        # 查找该toggle-item下的所有a标签
        a_tags = item.find_all('a')
        # 检查是否有a标签包含class="disabled"
        has_disabled = any('disabled' in (tag.get('class', []) or []) for tag in a_tags)
        if not has_disabled:
            filtered_homes.append(item)
    available_homes = filtered_homes
    logger.info(f"Found {len(available_homes)} available homes in available-homes container")
    
    for home in available_homes:
        # 初始化homesite对象
        homesite = {
            'images': [],
            'name': None,
            'plan': None,
            'url': None,
            'id': None,
            'address': None,
            'price': None,
            'beds': None,
            'baths': None,
            'sqft': None,
            'status': None,
            'image_url': None,
            'location': {
                'latitude': latitude,
                'longitude': longitude
            },
            'overview': "This beautiful new construction home features an open concept floor plan with modern finishes throughout."
        }
        
        try:
            # 提取链接和plan
            link = home.find('a', class_='CoveoResultLink')
            if link:
                # 检查房屋状态
                if 'disabled' in link.get('class', []):
                    homesite['status'] = 'Under Contract'
                else:
                    homesite['status'] = 'Available'

                # 提取URL和ID
                if 'href' in link.attrs:
                    href = link['href']
                    homesite['url'] = 'https://www.drhorton.com' + href if href.startswith('/') else href
                    parts = href.split('/')
                    if len(parts) >= 2:
                        id_match = re.search(r'^(\d+)', parts[-1])
                        if id_match:
                            homesite['id'] = id_match.group(1)
            
            # 提取图片URL
            card_image = home.find('div', class_='card-image')
            if card_image:
                # 检查style属性中的背景图片
                if 'style' in card_image.attrs:
                    style = card_image['style']
                    url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                    if url_match:
                        image_url = url_match.group(1)
                        if image_url.startswith('/-/'):
                            image_url = 'https://www.drhorton.com' + image_url
                        elif image_url.startswith('//'):
                            image_url = 'https:' + image_url
                        elif not image_url.startswith('http'):
                            image_url = 'https://www.drhorton.com' + image_url
                        homesite['image_url'] = image_url
                        homesite['images'].append(image_url)
                
                # 检查img标签
                img_tags = card_image.find_all('img')
                for img in img_tags:
                    src = img.get('src')
                    if src:
                        if src.startswith('/-/'):
                            src = 'https://www.drhorton.com' + src
                        elif src.startswith('//'):
                            src = 'https:' + src
                        elif not src.startswith('http'):
                            src = 'https://www.drhorton.com' + src
                        if src not in homesite['images']:
                            homesite['images'].append(src)
            
            # 提取card-content中的信息
            card_content = home.find('div', class_='card-content')
            if card_content:
                # 提取地址
                h3 = card_content.find('h3')
                if h3:
                    address_text = h3.text.strip()
                    homesite['address'] = address_text
                    if not homesite['name']:
                        homesite['name'] = address_text
                
                # 提取价格
                h2 = card_content.find('h2')
                if h2:
                    price_text = h2.get_text(strip=True)
                    if 'Under Contract' in price_text:
                        homesite['status'] = 'Under Contract'
                    else:
                        price_match = re.search(r'\$[\d,]+', price_text)
                        if price_match:
                            homesite['price'] = price_match.group(0)
                
                # 提取所有p标签的文本内容
                p_tags = card_content.find_all('p')
                for p in p_tags:
                    text = p.get_text(strip=True)
                    
                    # 提取beds
                    if 'Bed' in text:
                        beds_match = re.search(r'(\d+)\s*Bed', text)
                        if beds_match:
                            homesite['beds'] = beds_match.group(1)
                    
                    # 提取baths
                    if 'Bath' in text:
                        baths_match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', text)
                        if baths_match:
                            homesite['baths'] = baths_match.group(1)
                    
                    # 提取sqft
                    if 'Sq. Ft.' in text:
                        sqft_match = re.search(r'(\d+(?:,\d+)?)\s*Sq\.\s*Ft\.', text)
                        if sqft_match:
                            homesite['sqft'] = sqft_match.group(1).replace(',', '')
        
        except Exception as e:
            logger.error(f"Error processing home: {str(e)}")
            continue
        
        # 如果找到了homesite信息，添加到列表中
        if homesite['address'] or homesite['name']:
            homesites.append(homesite)
            logger.info(f"Added homesite: {homesite['address'] or homesite['name']} with {len(homesite['images'])} images")
    
    logger.info(f"Total homesites found: {len(homesites)}")
    return homesites

def process_raw_page(raw_page_path):
    """处理原始页面并生成JSON输出"""
    try:
        # 读取HTML文件
        with open(raw_page_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取基本信息
        price_from = extract_price_from(soup)
        home_details = extract_home_details(soup)
        stories_range = extract_stories_range(soup)
        
        # 提取 homesites
        homesites = extract_homesite_details(soup)
        
        # 提取 homeplans
        homeplans = extract_home_plans(soup)
        
        # 处理每个homeplan的详情页面
        logger.info(f"Processing {len(homeplans)} homeplan details...")
        for homeplan in homeplans:
            if homeplan.get('url'):
                try:
                    # 下载homeplan页面
                    homeplan_page = download_homesite_page(homeplan['url'])
                    if homeplan_page:
                        # 从页面提取楼层信息和图片
                        with open(homeplan_page, 'r', encoding='utf-8') as f:
                            page_content = f.read()
                        page_soup = BeautifulSoup(page_content, 'html.parser')
                        
                        # 提取楼层信息
                        property_details = page_soup.find('div', class_='property-details')
                        if property_details:
                            story_text = property_details.get_text()
                            story_match = re.search(r'(\d+(?:\.5)?)\s*Story', story_text)
                            if story_match:
                                stories = float(story_match.group(1))
                                # 创建floorplan_images数组
                                floorplan_images = []
                                num_floors = int(stories) if stories.is_integer() else int(stories + 0.5)
                                for i in range(1, num_floors + 1):
                                    floorplan_images.append({
                                        "name": f"{i}st Floor Floorplan" if i == 1 else f"{i}nd Floor Floorplan" if i == 2 else f"{i}rd Floor Floorplan",
                                        "image_url": None
                                    })
                                
                                # 提取图片URL
                                content_photos = page_soup.find_all('div', class_='content-photo')
                                for i, photo in enumerate(content_photos):
                                    if i < len(floorplan_images):
                                        img = photo.find('img')
                                        if img and img.get('src'):
                                            src = img['src']
                                            if src.startswith('//'):
                                                src = 'https:' + src
                                            elif not src.startswith('http'):
                                                src = 'https://www.drhorton.com' + src
                                            floorplan_images[i]['image_url'] = src
                                
                                # 添加到homeplan对象
                                homeplan['floorplan_images'] = floorplan_images
                                logger.info(f"Added {len(floorplan_images)} floorplan images to homeplan")
                        
                        # 删除临时文件
                        try:
                            os.remove(homeplan_page)
                        except:
                            pass
                        
                        # 添加延迟，避免请求过于频繁
                        time.sleep(random.uniform(2, 5))
                        
                except Exception as e:
                    logger.error(f"Error processing homeplan detail page: {str(e)}")
                    continue
        
        # 处理每个homesite的详情页面
        logger.info(f"Processing {len(homesites)} homesite details...")
        for homesite in homesites:
            if homesite.get('url'):
                try:
                    # 下载homesite页面
                    homesite_page = download_homesite_page(homesite['url'])
                    if homesite_page:
                        # 从页面提取plan和images信息
                        info = extract_homesite_page_info(homesite_page)
                        if info.get('plan'):
                            homesite['plan'] = info['plan']
                            logger.info(f"Updated plan for homesite {homesite.get('address')}: {homesite['plan']}")
                        if info.get('images'):
                            homesite['images'] = info['images']
                            logger.info(f"Updated images for homesite {homesite.get('address')}: {len(info['images'])} images found")
                        
                        # 删除临时文件
                        try:
                            os.remove(homesite_page)
                        except:
                            pass
                        
                        # 添加延迟，避免请求过于频繁
                        time.sleep(random.uniform(2, 5))
                        
                except Exception as e:
                    logger.error(f"Error processing homesite detail page for {homesite.get('address')}: {str(e)}")
        
        # 提取其他信息
        nearby_places = extract_nearby_places(soup)
        amenities_list = extract_amenities(soup)
        nearby_schools = extract_nearby_schools(soup)
        
        # 更新price_range
        max_price = None
        for homesite in homesites:
            if homesite.get('price'):
                price_match = re.search(r'\$[\d,]+', str(homesite['price']))
                if price_match:
                    current_price = price_match.group(0)
                    if not max_price or current_price > max_price:
                        max_price = current_price
        
        # 准备输出数据
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "name": extract_community_name(soup),
            "status": None,
            "price_from": price_from,
            "address": extract_address(soup),
            "phone": extract_phone(soup),
            "description": extract_description(soup),
            "images": extract_images(soup),
            "location": {
                "latitude": extract_latitude(soup),
                "longitude": extract_longitude(soup),
                "address": {
                    "city": None,
                    "state": None,
                    "market": None
                }
            },
            "details": {
                "price_range": f"{price_from} - {max_price}" if max_price else price_from,
                "sqft_range": home_details['sqft_range'],
                "bed_range": home_details['bed_range'],
                "bath_range": home_details['bath_range'],
                "stories_range": stories_range,
                "community_count": extract_community_count(soup)
            },
            "amenities": amenities_list,
            "homeplans": homeplans,
            "homesites": homesites,
            "nearbyplaces": nearby_places,
            "collections": [
                {
                    "name": "Main Collection",
                    "id": "0",
                    "isActive": True,
                    "nearbySchools": nearby_schools
                }
            ]
        }
        
        # 保存JSON文件
        output_file = os.path.join(os.path.dirname(raw_page_path), 'drhorton_output.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully processed {raw_page_path} and saved to {output_file}")
        
    except Exception as e:
        print(f"Error processing page: {str(e)}")

def download_homesite_page(url):
    """下载homesite详情页面并保存到临时文件"""
    try:
        # 随机延迟开始请求
        time.sleep(random.uniform(2, 5))
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # 添加更多的浏览器选项来模拟真实用户
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 使用最新的 Chrome User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        # 修改 navigator.webdriver 属性
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
            '''
        })
        
        logger.info(f"Downloading homesite page: {url}")
        
        # 随机延迟页面加载前
        time.sleep(random.uniform(2, 5))
        
        driver.get(url)
        
        # 等待页面加载，添加随机延迟
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(random.uniform(3, 6))
        
        # 模拟真实用户行为：随机滚动
        for _ in range(random.randint(3, 6)):
            scroll_height = random.randint(300, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            time.sleep(random.uniform(0.5, 1.5))
        
        # 滚动到页面底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 3))
        
        # 滚动回页面顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(1, 2))
        
        # 获取页面内容
        page_content = driver.page_source
        
        # 保存到临时文件
        temp_file = f'homesite_page_{int(time.time())}_{random.randint(1000, 9999)}.html'
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(page_content)
        
        logger.info(f"Successfully downloaded and saved homesite page to {temp_file}")
        
        # 随机延迟结束
        time.sleep(random.uniform(1, 3))
        
        return temp_file
        
    except Exception as e:
        logger.error(f"下载homesite页面时出错 {url}: {str(e)}")
        # 出错后的更长随机延迟
        time.sleep(random.uniform(10, 15))
        return None
    
    finally:
        if 'driver' in locals():
            driver.quit()
            # 处理每个房屋之间的随机延迟
            time.sleep(random.uniform(5, 10))

def main():
    """主函数"""
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='Scrape D.R. Horton community pages')
        parser.add_argument('--batch', action='store_true', help='Process all URLs from florida_links.json')
        parser.add_argument('--url', help='Process a single URL')
        args = parser.parse_args()

        # 确保输出目录存在
        output_dir = 'data/drhorton'
        os.makedirs(output_dir, exist_ok=True)
        
        if args.batch:
            try:
                # 先运行get_drhorton_api_links.py生成florida_links.json
                logger.info("Running get_drhorton_api_links.py to generate URL list...")
                current_dir = os.path.dirname(os.path.abspath(__file__))
                api_links_script = os.path.join(current_dir, 'get_drhorton_api_links.py')
                
                if not os.path.exists(api_links_script):
                    logger.error(f"Could not find {api_links_script}")
                    return
                
                # 运行脚本
                os.system(f'python "{api_links_script}"')
                
                # 等待文件生成
                time.sleep(5)
                
                # 检查多个可能的文件位置
                possible_paths = [
                    'florida_links.json',
                    'data/florida_links.json',
                    'data/drhorton/florida_links.json',
                    os.path.join(current_dir, 'florida_links.json'),
                    os.path.join(current_dir, 'data/florida_links.json'),
                    os.path.join(current_dir, 'data/drhorton/florida_links.json')
                ]
                
                json_file = None
                for path in possible_paths:
                    if os.path.exists(path):
                        json_file = path
                        logger.info(f"Found florida_links.json at {path}")
                        break
                
                if not json_file:
                    logger.error("Could not find florida_links.json in any expected location")
                    return
                
                # 读取florida_links.json
                with open(json_file, 'r', encoding='utf-8') as f:
                    urls = json.load(f)
                
                if not urls:
                    logger.error("No URLs found in florida_links.json")
                    return
                
                logger.info(f"Found {len(urls)} URLs to process")
                
                # 处理每个URL
                for i, url in enumerate(urls, 1):
                    try:
                        logger.info(f"Processing URL {i}/{len(urls)}")
                        fetch_page(url, output_dir)
                        time.sleep(2)  # 添加延迟以避免请求过于频繁
                    except Exception as e:
                        logger.error(f"Failed to process URL {url}: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error in batch processing: {str(e)}")
                logger.exception("详细错误信息：")
                return
                
        elif args.url:
            # 处理单个指定的URL
            fetch_page(args.url, output_dir)
        else:
            # 处理单个默认URL
            #default_url = "https://www.drhorton.com/north-carolina/raleigh-durham/apex/the-townes-at-horton-park"
            # default_url = "https://www.drhorton.com/florida/north-florida/st-augustine/cordera-townhomes-express"
            #default_url = "https://www.drhorton.com/alabama/baldwin-county/foley/roberts-cove"
            default_url = "https://www.drhorton.com/georgia/southern-georgia/bainbridge/southgate"
            fetch_page(default_url, output_dir)
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        logger.exception("详细错误信息：")

if __name__ == "__main__":
    main() 