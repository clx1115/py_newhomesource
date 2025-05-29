# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import logging
import os
import sys
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
sys.stdout.reconfigure(encoding='utf-8')  # 设置标准输出编码为UTF-8
logger = logging.getLogger(__name__)

def extract_community_info(html_content, driver=None):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # 把soup保存到soup.html
        with open('data0318/soup_StoreyCreek.html', 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        community_info = {
            'timestamp': datetime.now().isoformat(),
            'name': None,
            'status': None,
            'price_from': None,
            'address': None,
            'phone': None,
            'description': None,
            'images': [],  # 确保初始化时包含images字段
            'location': {
                'latitude': None,
                'longitude': None,
                'address': {
                    'city': None,
                    'state': None,
                    'market': None
                }
            },
            'details': {},
            'amenities': [],
            'homeplans': [],  # 房源计划列表
            'homesites': [],  # 新增homesites字段
            'nearbyplaces': [],  # 新增nearbyplaces字段
            'collections': []  # 新增collections字段
        }
        
        # 提取社区名称
        # community_name = soup.find('h1')
        # if community_name:
        #     community_info['name'] = community_name.text.strip()
            
        # # 提取社区轮播图片 - 获取所有图片
        # carousel_images = soup.find_all('img', class_=lambda x: x and 'Image_image__3QFzw' in x and 'CommunityPageCarousel_slideImg__6k4dR' in x)
        # if carousel_images:
        #     valid_images = []
        #     for img in carousel_images:
        #         src = img.get('src')
        #         if src and not src.startswith('data:'):  # 排除base64图片
        #             valid_images.append(src)
            
        #     if valid_images:
        #         community_info['images'] = valid_images
        #         logger.info(f"提取到{len(valid_images)}张社区轮播图片")
        #         for img_url in valid_images:
        #             logger.info(f"图片URL: {img_url}")
        #     else:
        #         logger.warning("未找到有效的轮播图片URL")
        # else:
        #     logger.warning("未找到轮播图片元素")

        # 获取基本信息
        base_info = {
            'timestamp': datetime.now().isoformat(),
            'name': soup.find('h1').text.strip() if soup.find('h1') else None,
            'status': None,
            'price_from': None,
            'address': None,
            'phone': None,
            'description': None
        }
        
        # 提取状态和价格信息
        # 尝试不同的类名和结构来查找价格信息
        status_price = soup.find('p', class_=lambda x: x and 'Typography_' in x and 'price' in x.lower())
        if not status_price:
            status_price = soup.find('div', class_=lambda x: x and 'price' in x.lower())
        
        if status_price:
            text = status_price.text.strip()
            if 'Actively selling' in text:
                base_info['status'] = 'Actively selling'
            elif 'From the upper' in text:
                base_info['price_from'] = text
            elif 'From' in text:
                base_info['price_from'] = text
                
        # 如果没有找到价格信息，尝试其他方法
        if not base_info.get('price_from'):
            # 尝试查找包含价格的span或div元素
            price_elements = soup.find_all(['span', 'div'], string=lambda x: x and any(keyword in str(x).lower() for keyword in ['from', '$', 'price']))
            for elem in price_elements:
                text = elem.text.strip()
                if 'from' in text.lower() or '$' in text:
                    base_info['price_from'] = text
                    break
        
        # 提取地址和电话
        address_phone_div = soup.find('div', class_=lambda x: x and 'HeroInformation_addressPhone__' in x)
        if address_phone_div:
            paragraphs = address_phone_div.find_all('p')
            if len(paragraphs) >= 1:
                base_info['address'] = paragraphs[0].text.strip()
            if len(paragraphs) >= 2:
                base_info['phone'] = paragraphs[1].text.strip()
        
        # 获取__NEXT_DATA__脚本数据
        script_data = soup.find('script', {'id': '__NEXT_DATA__'})
        if script_data:
            try:
                next_data = json.loads(script_data.string)
                apollo_state = next_data['props']['pageProps']['initialApolloState']
                # mpc_data = next_data['props']['pageProps']['initialApolloState'].get('MpcType:m_1905', {})
                mpc_data = {}
                mpc_keys = [key for key in apollo_state.keys() if key.startswith('MpcType:m_')]
                if mpc_keys:
                    mpc_data = apollo_state[mpc_keys[0]]
                # 获取heroImage URL
                hero_image = mpc_data.get('heroImage', {})
                if hero_image and 'url' in hero_image:
                    community_info['images'] = community_info.get('images', [])
                    community_info['images'].append(hero_image['url'])
                    logger.info(f"提取到heroImage URL: {hero_image['url']}")
                
                # 更新community_info，保留之前提取的信息
                updated_info = {
                    'location': {
                        'latitude': mpc_data.get('latitude'),
                        'longitude': mpc_data.get('longitude'),
                        'address': {
                            'city': mpc_data.get('city', {}).get('name'),
                            'state': mpc_data.get('state', {}).get('name'),
                            'market': mpc_data.get('market', {}).get('name')
                        }
                    },
                    'details': {
                        'price_range': mpc_data.get('customPrice'),
                        'sqft_range': mpc_data.get('sqftRange'),
                        'bed_range': mpc_data.get('bedRange'),
                        'bath_range': mpc_data.get('bathRange'),
                        'stories_range': mpc_data.get('storiesRange'),
                        'community_count': mpc_data.get('communityCount')
                    }
                }
                
                # 更新community_info，保留已有字段
                community_info.update({
                    **base_info,
                    'location': updated_info['location'],
                    'details': updated_info['details']
                })
                
                if mpc_data and 'shortIntroText' in mpc_data:
                    community_info['description'] = mpc_data['shortIntroText']
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"解析__NEXT_DATA__时出错: {str(e)}")
        
        # 提取配套设施
        if 'amenityInfo' in mpc_data and 'amenities' in mpc_data['amenityInfo']:
            for amenity in mpc_data['amenityInfo']['amenities']:
                community_info['amenities'].append({
                    'name': amenity.get('name'),
                    'description': amenity.get('desc'),
                    'icon_url': amenity.get('icon', {}).get('url')
                })
        
        # 提取homesites信息
        homesites = extract_homesites(driver, WebDriverWait(driver, 60))
        if homesites:
            community_info['homesites'] = homesites
            logger.info(f"成功提取到 {len(homesites)} 个homesites")
        else:
            logger.warning('未找到homesites数据')
            
        # 提取房源计划
        plans_div = soup.find('div', class_=lambda x: x and 'FutureReleasesPanel_content__' in x)
        if plans_div:
            plan_links = plans_div.find_all('a')
            for link in plan_links:
                # 获取房源名称
                plan_name = link.find('h4')
                if plan_name:
                    plan_name = plan_name.text.strip()
                else:
                    continue
                
                # 获取房源链接
                plan_url = link.get('href')
                
                # 获取房源详细信息
                plan_info = {
                    'name': plan_name,
                    'url': plan_url,
                    'details': {}
                }
                
                # 获取价格信息
                price_span = link.find('span', class_=lambda x: x and 'FutureReleasesCard_price__' in x)
                if price_span:
                    plan_info['details']['price'] = price_span.text.strip()
                
                # 获取详细信息（面积、卧室数等）
                meta_details = link.find('div', class_=lambda x: x and 'FutureReleasesCard_metaDetails__' in x)
                if meta_details:
                    meta_items = meta_details.find_all('span', class_=lambda x: x and 'MetaDetails_metaItem__' in x)
                    for item in meta_items:
                        text = item.text.strip().lower()
                        if 'bd' in text:
                            plan_info['details']['beds'] = text
                        elif 'ba' in text:
                            if 'half ba' in text:
                                plan_info['details']['half_baths'] = text
                            else:
                                plan_info['details']['baths'] = text
                        elif 'ft²' in text or 'ft2' in text:
                            plan_info['details']['sqft'] = text
                
                # 获取状态信息
                status_span = link.find('span', string=lambda x: x and 'Actively selling' in x)
                if status_span:
                    plan_info['details']['status'] = 'Actively selling'
                
                # 获取图片信息
                img = link.find('img')
                if img:
                    src = img.get('src', '')
                    if src:
                        plan_info['details']['image_url'] = src.split('?')[0]  # 移除URL参数
                
                community_info['homeplans'].append(plan_info)
                
                # 记录日志
                logger.info(f"提取到房源计划: {plan_name}")
        
        return community_info
            
    except Exception as e:
        logger.error(f"解析社区信息时出错: {e}")
        return None

def extract_nearby_places(html_content):
    """提取附近地点信息"""
    soup = BeautifulSoup(html_content, 'html.parser')
    nearby_places = []
    
    # 查找所有地点项
    places_list = soup.find('div', class_='PointsOfInterestList_list__8yKUV')
    if places_list:
        place_items = places_list.find_all('div', class_='PointsOfInterestListItem_listItem__cJ17m')
        for item in place_items:
            place_info = {
                'name': None,
                'category': None,
                'distance': None,
                'rating': None,
                'reviews': None
            }
            
            # 提取名称和类别信息
            info_div = item.find('div', class_='PointsOfInterestListItem_info__hg0kN')
            if info_div:
                # 提取名称
                name_elem = info_div.find('p', class_=lambda x: x and 'headline3' in x)
                if name_elem:
                    place_info['name'] = name_elem.text.strip()
                
                # 提取类别和距离
                details_elem = info_div.find('p', class_='bodycopySmall')
                if details_elem:
                    details_text = details_elem.text.strip()
                    if '•' in details_text:
                        category, distance = details_text.split('•')
                        place_info['category'] = category.strip()
                        place_info['distance'] = distance.strip()
            
            # 提取评分信息
            rating_div = item.find('div', class_='Rating_root__i2oym')
            if rating_div:
                # 提取评分
                rating_label = rating_div.get('aria-label', '')
                if 'out of 5 stars' in rating_label:
                    try:
                        rating = float(rating_label.split(' ')[0])
                        place_info['rating'] = rating
                    except (ValueError, IndexError):
                        pass
                
                # 提取评论数
                reviews_elem = rating_div.find('span', class_='caption')
                if reviews_elem:
                    try:
                        place_info['reviews'] = int(reviews_elem.text.strip())
                    except ValueError:
                        pass
            
            nearby_places.append(place_info)
    
    return nearby_places

def extract_collections(driver, wait):
    """从页面提取collections信息"""
    collections = []
    try:
        # 直接从页面源码提取
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 查找collections容器
        tabs_wrapper = soup.find('div', class_='TabsList_tabsWrapper__6txbc')
        if tabs_wrapper:
            # 查找所有collection按钮
            tab_buttons = tabs_wrapper.find_all('button', class_='TabsList_tab__w2V_x')
            for button in tab_buttons:
                try:
                    # 提取collection名称
                    span = button.find('span', class_='DynamicFontWeightText_text__K1JCq')
                    if span:
                        collection_info = {
                            'name': span.get('data-text') or span.text.strip(),
                            'id': button.get('data-testid', '').replace('header-tab-', ''),
                            'isActive': 'TabsList_activeTab__s1Yz1' in button.get('class', [])
                        }
                        collections.append(collection_info)
                        active_status = "活跃" if collection_info['isActive'] else "非活跃"
                        logging.info(f'提取到collection: {collection_info["name"]} (ID: {collection_info["id"]}, 状态: {active_status})')
                except Exception as e:
                    logging.error(f'处理单个collection时出错: {str(e)}')
                    continue
        
        if not collections:
            logging.warning('未找到任何collections数据')
            
    except Exception as e:
        logging.error(f'提取collections时出错: {str(e)}')
        logging.error(traceback.format_exc())
    
    return collections

def extract_homesite_info(driver, homesite_element):
    """从homesite元素中提取信息"""
    try:
        homesite = {
            'name': None,
            'plan': None,
            'id': None,
            'address': None,
            'price': None,
            'beds': None,
            'baths': None,
            'sqft': None,
            'status': None,
            'image_url': None,
            'url': None
        }
        # logging.info(f'homesite_element: {homesite_element}')
        # # 停止程序
        # input("Press Enter to continue...")
        # 提取链接和基本信息
        link = homesite_element.get('href')
        if link:
            homesite['url'] = link
            # 提取链接最后的数字作为ID
            homesite['id'] = link.split('/')[-1]
    
        # 获取详细信息
        if homesite['url']:  # 如果有URL才获取详细信息
            detailed_info = extract_homesite_details(driver, homesite['url'])
            # 确保不覆盖原有字段
            for key, value in detailed_info.items():
                if key not in homesite or homesite[key] is None:
                    homesite[key] = value

        # 提取listing数据
        listing_data = homesite_element.get('data-listing')
        if listing_data:
            try:
                listing = json.loads(listing_data)
                homesite['name'] = listing.get('name')
                homesite['id'] = listing.get('id')
            except json.JSONDecodeError:
                pass
        
        # 提取图片URL
        img = homesite_element.find('img')
        if img:
            homesite['image_url'] = img.get('src')

        # 提取价格
        # price_elem = homesite_element.find('h4', class_='HomesitesTableV3_price__JFoNm')
        price_elem = homesite_element.find('span', class_='HomesitesTableNew_wasPrice__mMVQd')
        
        if price_elem:
            homesite['price'] = price_elem.text.strip()

        # 提取地址和详细信息
        # details = homesite_element.find_all('span', class_='Typography_tagsAndLegalNew__lXvvj')
        # 查找所有class为'Typography_bodycopyExtraSmall__aPBwl HomesitesTableNew_itemCell__LjasJ'的p标签
        details = homesite_element.find_all('p', class_=lambda x: x and all(c in x for c in ['Typography_bodycopyExtraSmall__aPBwl', 'HomesitesTableNew_itemCell__LjasJ']))
        
        for detail in details:
            text = detail.text.strip()
            
            if 'bd' in text and 'ba' in text and 'ft²' in text:
                # 提取床数、浴室数和面积
                parts = text.split('•')
                total = 0
                for part in parts:
                    if 'bd' in part:
                        homesite['beds'] = part.strip().replace('bd', '').strip()
                    elif 'ft²' in part or 'ft2' in part:
                        homesite['sqft'] = part.strip().replace('ft²', '').replace('ft2', '').strip()
                    elif 'half ba' in part:
                        total += int(part.strip().replace('half ba', '').strip()) * 0.5
                    elif 'ba' in part:
                        total += int(part.strip().replace('ba', '').strip())
                homesite['baths'] = total
            elif 'Circle' in text or 'Drive' in text or 'Street' in text or 'Road' in text:
                # 提取地址
                homesite['address'] = text.strip()
                homesite['name'] = text.strip()
        #
        if not homesite['address']:
            address_details = homesite_element.find_all('p', class_=lambda x: x and all(c in x for c in ['bodycopyExtraSmall', 'Typography_bodycopyExtraSmall__aPBwl']))
            
            # 停止程序
            if len(address_details) >= 4:  # 确保有足够的元素
                address_detail = address_details[3].text.strip()
                homesite['address'] = address_detail
                homesite['plan'] = address_details[0].text.strip()
            logger.info(f"找到 {len(address_details)} 个地址相关元素")


        # 提取状态
        # status_circle = homesite_element.find('div', class_='HomesitesTableV3_statusCircle__jr4JW')
        status_circle = homesite_element.find('div', class_=lambda x: x and all(c in x for c in ['HomesitesTableNew_statusCircle__5200a']))
        
        # logging.info(f'status_circle: {status_circle.get("class", [])}')
        # input("Press Enter to continue...")
        if status_circle:
            status_circle_classes = status_circle.get('class', [])
            for status_class in status_circle_classes:
                if 'HomesitesTableNew_moveInReady__' in status_class:
                    homesite['status'] = 'Move-in Ready'
                elif 'HomesitesTableNew_comingSoon__' in status_class:
                    homesite['status'] = 'Coming Soon'
                elif 'HomesitesTableNew_soldOut__' in status_class:
                    homesite['status'] = 'Sold Out'
            # if 'HomesitesTableV3_moveInReady__' in status_circle.get('class', []):
            # if 'HomesitesTableNew_moveInReady__' in status_circle.get('class', []):
            #     homesite['status'] = 'Move-in Ready'
            # # 可以添加其他状态的判断
            
            # if 'HomesitesTableNew_comingSoon__' in status_circle.get('class', []):
            #     homesite['status'] = 'Coming Soon'
            
            # if 'HomesitesTableNew_soldOut__' in status_circle.get('class', []):
            #     homesite['status'] = 'Sold Out'
        return homesite
    except Exception as e:
        logging.error(f'提取homesite信息时出错: {str(e)}')
        return None

def extract_homesites(driver, wait):
    """提取所有homesites信息"""
    homesites = []
    seen_ids = set()  # 用于跟踪已经处理过的homesite ID
    
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # homesite_elements = soup.find_all('a', class_='HomesitesTableV3_rowButton__VGykR')
        homesite_elements = soup.find_all('a', class_='HomesitesTableNew_rowButton__EDamq')
        
        for element in homesite_elements:
            homesite = extract_homesite_info(driver, element)
            if homesite and homesite['id']:
                # 只添加未处理过的homesite
                if homesite['id'] not in seen_ids:
                    seen_ids.add(homesite['id'])
                    homesites.append(homesite)
                    logging.info(f'提取到homesite: {homesite["address"] or homesite["id"]}')
        
        if not homesites:
            logging.warning('未找到任何homesites')
            
    except Exception as e:
        logging.error(f'提取homesites时出错: {str(e)}')
        logging.error(traceback.format_exc())
    
    return homesites

def extract_homesite_details(driver, homesite_url):
    """提取房源详细信息"""
    full_url = f"https://www.lennar.com{homesite_url}"
    logging.info(f"正在访问房源页面: {full_url}")
    driver.get(full_url)
    
    try:
        # 等待页面加载完成
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "__NEXT_DATA__")))
        
        # 获取页面源码并解析
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 获取__NEXT_DATA__脚本数据
        script_data = soup.find('script', {'id': '__NEXT_DATA__'})
        if not script_data:
            logging.warning(f"未找到__NEXT_DATA__脚本: {full_url}")
            return {}
            
        # 解析JSON数据
        next_data = json.loads(script_data.string)
        apollo_state = next_data['props']['pageProps']['initialApolloState']
        root_query = apollo_state.get('ROOT_QUERY', {})
        
        # 从ROOT_QUERY中获取community和homesite的引用
        community_ref = None
        homesite_ref = None
        
        # 遍历ROOT_QUERY的键以找到community和homesite
        for key, value in root_query.items():
            if isinstance(value, dict) and '__ref' in value:
                if key.startswith('community'):
                    community_ref = value['__ref']
                elif key.startswith('homesite'):
                    homesite_ref = value['__ref']
        
        # 获取经纬度信息
        latitude = None
        longitude = None
        if community_ref:
            community_data = apollo_state.get(community_ref, {})
            latitude = community_data.get('latitude')
            longitude = community_data.get('longitude')
        
        # 获取overview信息
        overview = None
        if homesite_ref:
            homesite_data = apollo_state.get(homesite_ref, {})
            overview = homesite_data.get('overview')
        
        # 获取图片URL
        images = []
        if homesite_ref:
            homesite_data = apollo_state.get(homesite_ref, {})
            elevation_image = homesite_data.get('elevationImage', {})
            image_url = elevation_image.get('image', {}).get('url') if elevation_image else None
            if image_url:
                images.append(image_url)
        
        # 获取walkthrough页面的图片
        walkthrough_images = extract_homesite_walkthrough(driver, homesite_url)
        if walkthrough_images:
            images.extend(walkthrough_images)
            
        # 只返回新增字段，不覆盖原有字段
        return {
            'latitude': latitude,
            'longitude': longitude,
            'overview': overview,
            'images': images
        }
    except Exception as e:
        logging.error(f"解析房源详情时出错: {str(e)}")
        return {}

def extract_homesite_walkthrough(driver, homesite_url):
    """提取房源walkthrough页面的图片"""
    try:
        walkthrough_url = f"https://www.lennar.com{homesite_url}/walkthrough"
        logging.info(f"正在访问walkthrough页面: {walkthrough_url}")
        driver.get(walkthrough_url)
        
        # 等待页面加载
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'WalkthroughModalContent_roomWrapper__LmRmO')))
        
        # 滚动页面以触发图片加载
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # 等待图片加载
        
        # 尝试点击所有房间标签以加载更多图片
        try:
            room_tabs = driver.find_elements(By.CLASS_NAME, 'WalkthroughModalContent_roomTab__')
            for tab in room_tabs:
                driver.execute_script("arguments[0].click();", tab)
                time.sleep(1)  # 等待新图片加载
        except Exception as e:
            logging.warning(f"点击房间标签时出错: {str(e)}")
        
        # 获取页面源码
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 提取所有房间图片
        images = []
        # room_wrappers = soup.find_all('div', class_='WalkthroughModalContent_roomWrapper__LmRmO')
        # for wrapper in room_wrappers:
        #     room_images = wrapper.find_all('img', class_='Image_image__3QFzw')
        #     for img in room_images:
        #         src = img.get('src')
        #         if src and not src.startswith('data:'):  # 排除base64图片
        #             if src not in images:  # 避免重复图片
        #                 images.append(src)
        #                 logging.info(f"提取到walkthrough图片: {src}")
        
        # 如果没有找到图片，尝试提取其他可能的图片容器
        if not images:
            all_images = soup.find_all('img', class_='Image_image__3QFzw')
            for img in all_images:
                src = img.get('src')
                if src and not src.startswith('data:'):
                    if src not in images and 'room' in src.lower():  # 确保是房间图片
                        images.append(src)
                        logging.info(f"提取到其他房间图片: {src}")
        
        return images
    except Exception as e:
        logging.error(f"提取walkthrough图片时出错: {str(e)}")
        return []

def extract_included_features(driver, url):
    try:
        included_url = url + '/included'
        driver.get(included_url)
        time.sleep(2)  # 等待页面加载
        
        features = []
        sections = driver.find_elements(By.CLASS_NAME, 'IncludedFeaturesModal_sectionWrapper__CQEsH')
        
        for section in sections:
            data_index = section.get_attribute('data-index')
            items = section.find_elements(By.CLASS_NAME, 'IncludedFeaturesContent_textItem__vpcBa')
            
            for item in items:
                feature = {
                    'section_index': data_index,
                    'description': item.text
                }
                features.append(feature)
                
        return features
    except Exception as e:
        logging.error(f"提取included features时出错: {str(e)}")
        return []

def extract_nearby_schools(driver, wait, collection_url):
    try:
        # 构建nearby-schools URL
        schools_url = collection_url + '/nearby-schools'
        logging.info(f"正在访问学校页面: {schools_url}")
        driver.get(schools_url)
        time.sleep(5)  # 增加等待时间到5秒
        
        schools = []
        try:
            # 等待并获取学校列表，增加超时时间到30秒
            wait_schools = WebDriverWait(driver, 30)
            school_items = wait_schools.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'SchoolList_item__jCc_G')))
            
            if not school_items:
                logging.warning(f"未找到学校信息: {schools_url}")
                return []
                
            for item in school_items:
                try:
                    # 提取学校信息
                    info_div = item.find_element(By.CLASS_NAME, 'SchoolListItem_info__R0qZz')
                    name = info_div.find_element(By.CLASS_NAME, 'SchoolListItem_label__y8hWW').text
                    details = info_div.find_elements(By.CLASS_NAME, 'bodycopySmall')
                    type_and_grades = details[0].text if len(details) > 0 else ''
                    district = details[1].text if len(details) > 1 else ''
                    
                    # 提取评级信息
                    rating_div = item.find_element(By.CLASS_NAME, 'SchoolListItem_rating__jZkcG')
                    grade = ''
                    try:
                        grade_div = rating_div.find_element(By.CLASS_NAME, 'SchoolListItem_grade___hRgP')
                        grade = grade_div.text if grade_div else ''
                    except:
                        pass
                    
                    # 提取排名信息
                    ranking = ''
                    try:
                        ranking = rating_div.find_element(By.CLASS_NAME, 'caption').text
                    except:
                        pass
                    
                    # 提取Niche.com链接
                    link = ''
                    try:
                        link_elem = item.find_element(By.CLASS_NAME, 'SchoolListItem_link__rZVjX')
                        link = link_elem.get_attribute('href')
                    except:
                        pass
                    
                    school = {
                        'name': name,
                        'type_and_grades': type_and_grades,
                        'district': district,
                        'grade': grade,
                        'ranking': ranking,
                        'niche_link': link
                    }
                    schools.append(school)
                    logging.info(f"提取到学校信息: {name}")
                except Exception as e:
                    logging.error(f"提取单个学校信息时出错: {str(e)}")
                    continue
            
            return schools
        except TimeoutException:
            logging.error(f"等待学校列表超时: {schools_url}")
            return []
    except Exception as e:
        logging.error(f"提取nearby schools时出错: {str(e)}")
        return []

def extract_floorplan_images(driver, homeplan_url):
    """提取homeplan页面的floorplan图片信息"""
    floorplan_images = []
    
    try:
        # 跳转到homeplan页面
        driver.get(homeplan_url)
        time.sleep(2)  # 等待页面加载
        
        # 获取页面源码
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 查找__NEXT_DATA__脚本
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
        if next_data_script:
            # 解析JSON数据
            next_data = json.loads(next_data_script.string)
            
            # 从initialApolloState中获取数据
            apollo_state = next_data.get('props', {}).get('pageProps', {}).get('initialApolloState', {})
            
            # 遍历所有键值对查找PlanType
            for key, value in apollo_state.items():
                if isinstance(value, dict) and value.get('__typename') == 'PlanType':
                    # 提取floorplans数据
                    floorplans = value.get('floorplans', [])
                    for floor in floorplans:
                        floor_name = floor.get('name', '')
                        default_image = floor.get('default', {}).get('image', {})
                        if floor_name and default_image:
                            image_url = default_image.get('url')
                            if image_url:
                                floorplan_images.append({
                                    'name': f"{floor_name} Floorplan",
                                    'image_url': image_url
                                })
                                logging.info(f'成功提取floorplan图片: {floor_name}')
                    
                    # # 提取外观图片
                    # elevation_images = value.get('elevationImages', [])
                    # for elevation in elevation_images:
                    #     image = elevation.get('image', {})
                    #     title = elevation.get('title', '')
                    #     if image and title:
                    #         image_url = image.get('url')
                    #         if image_url:
                    #             floorplan_images.append({
                    #                 'name': title,
                    #                 'image_url': image_url
                    #             })
                    #             logging.info(f'成功提取外观图片: {title}')
                    
                    break  # 找到PlanType后退出循环
    
    except Exception as e:
        logging.error(f'提取floorplan图片时出错: {str(e)}')
    
    return floorplan_images

def fetch_page():
    # url = "https://www.lennar.com/new-homes/north-carolina/raleigh/apex/carolina-springs"
    # url = "https://www.lennar.com/new-homes/south-carolina/charlotte/fort-mill/elizabeth"
    # url = "https://www.lennar.com/new-homes/california/la-orange-county/irvine/great-park-neighborhoods"
    # url = "https://www.lennar.com/new-homes/north-carolina/raleigh/durham/triple-crown"
    
    url = "https://www.lennar.com/new-homes/florida/orlando/kissimmee/storey-creek"
    # url = "https://www.lennar.com/new-homes/florida/orlando/kissimmee/tohoqua"
    # url = "https://www.lennar.com/new-homes/florida/orlando/clermont/wellness-ridge"
    # url = "https://www.lennar.com/new-homes/florida/orlando/orlando/everbe"
    
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.page_load_strategy = 'eager'  # 添加页面加载策略
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(60)  # 增加超时时间
        logger.info("开始获取页面内容，时间：" + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        driver.get(url)

        wait = WebDriverWait(driver, 30)  # 增加等待时间
        time.sleep(10)  # 增加等待时间
        logger.info("等待结束，时间：" + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        main_page_source = driver.page_source
        
        # 保存HTML内容到文件
        os.makedirs('data0318', exist_ok=True)  # 确保data目录存在
        with open('data0318/pageLennar_StoreyCreek.html', 'w', encoding='utf-8') as f:
            f.write(main_page_source)
        logger.info("页面HTML已保存到 data0318/pageLennar_StoreyCreek.html")
        # 提取collections信息并更新community_info
        collections = extract_collections(driver, wait)
        # 提取主页面信息
        community_info = extract_community_info(main_page_source, driver)
        if not community_info:
            logger.error("无法提取社区信息，使用默认值")
            community_info = {
                'timestamp': datetime.now().isoformat(),
                'name': None,
                'status': None,
                'price_from': None,
                'address': None,
                'phone': None,
                'description': None,
                'location': None,
                'homesites': [],
                'homeplans': [],
                'collections': [],
                'nearbyplaces': [],
                'images': []  # 确保images字段存在
            }
        
        
        if collections:
            # 为每个collection添加nearbySchools信息
            for collection in collections:
                # 构建collection URL
                collection_name = collection['name'].lower().replace(' ', '-')
                collection_url = url + '/' + collection_name
                collection['nearbySchools'] = extract_nearby_schools(driver, wait, collection_url)
            community_info['collections'] = collections
            
        if community_info:
            # 访问nearby-places页面
            nearby_url = url + '/nearby-places'
            driver.get(nearby_url)
            time.sleep(5)  # 等待动态内容加载
            
            # 等待附近地点列表加载
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "PointsOfInterestList_list__8yKUV")))
                nearby_page_source = driver.page_source
                
                # 提取附近地点信息
                nearby_places = extract_nearby_places(nearby_page_source)
                community_info['nearbyplaces'] = nearby_places
                logger.info(f"提取到{len(nearby_places)}个附近地点")
            except Exception as e:
                logger.error(f"提取附近地点信息时出错: {str(e)}")
            
            # 为每个plan添加includedFeatures字段
            for plan in community_info['homeplans']:
                logging.info(f"提取到房源计划: {plan['name']}")
                plan['includedFeatures'] = extract_included_features(driver, "https://www.lennar.com" + plan['url'])
            
            # 为每个plan添加floorplan_images字段
            for plan in community_info['homeplans']:
                logging.info(f"提取房源计划图片: {plan['name']}")
                plan['floorplan_images'] = extract_floorplan_images(driver, "https://www.lennar.com" + plan['url'])
            
            # 确保输出目录存在
            os.makedirs('data0318', exist_ok=True)
            
            # 使用UTF-8编码保存JSON文件
            with open('data0318/Lennar_community_info_StoreyCreek.json', 'w', encoding='utf-8') as f:
                json.dump(community_info, f, indent=2, ensure_ascii=False)
            
            print("\n提取的社区信息:")
            # print(json.dumps(community_info, indent=2, ensure_ascii=False))
            print("\n社区信息已保存到 data0318/Lennar_community_info_StoreyCreek.json")
        else:
            print("提取社区信息失败")
    
    except Exception as e:
        print(f"获取页面时出错: {str(e)}")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    fetch_page()
