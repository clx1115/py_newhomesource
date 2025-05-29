import json
import asyncio
import random
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import time
from bs4 import BeautifulSoup
from datetime import datetime
import os

async def extract_promo_info(url, crawler):
    # Define the promo extraction schema
    promo_schema = {
        "name": "Community Promos",
        "baseSelector": ".nhs-c-special-offers__card",  # Base container for promotions
        "fields": [
            {"name": "promo_title_element", "selector": "[data-qa='special_offers_title_card']", "type": "html"},
            {"name": "promo_content_element", "selector": "[data-qa='special_offers_card_content']", "type": "html"},
            {"name": "promo_link_element", "selector": "[data-qa='special_offers_card_link']", "type": "html"},
            {"name": "promo_card_element", "selector": ".nhs-c-special-offers__card", "type": "html"},  # 使用完整的类名选择器
            # 同时保留纯文本内容
            {"name": "promo_title", "selector": "[data-qa='special_offers_title_card']", "type": "text"},
            {"name": "promo_content", "selector": "[data-qa='special_offers_card_content']", "type": "text"},
            {"name": "promo_link", "selector": "[data-qa='special_offers_card_link']", "type": "attribute", "attribute": "href"}
        ]
    }
    extraction_strategy = JsonCssExtractionStrategy(promo_schema, verbose=True)
    
    result = await crawler.arun(
        url=url,
        extraction_strategy=extraction_strategy,
        cache_mode=True,
        simulate_user=True,
        override_navigator=True
    )
    if result.success and result.extracted_content:
        return json.loads(result.extracted_content)
    return []

async def extract_image_info(url, crawler):
    try:
        promo_schema = {
            "name": "Community Promos",
            "baseSelector": ".nhs_DetailTileMain",  # Base container for promotions
            "fields": [
                {"name": "image", "selector": "img", "type": "attribute", "attribute": "src"} 
            ]
        }
        
        extraction_strategy = JsonCssExtractionStrategy(promo_schema, verbose=True)
        
        result = await crawler.arun(
            url=url,
            extraction_strategy=extraction_strategy,
            cache_mode=True,
            simulate_user=True,
            override_navigator=True
        )
        try:
            # Initialize BeautifulSoup
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # Find the script tag containing image data
            script_tag = soup.find('script', {'data-component': 'fullImageViewerData'})
            if not script_tag:
                print("No image data script tag found")
                return []
                
            # Parse JSON data from script tag
            try:
                image_data = json.loads(script_tag.string)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON data: {e}")
                return []
                
            # Extract specified fields
            extracted_data = {}
            # detail address = Addr, City StateAbbr Zip
            fields_to_extract = [
                "State", "StateAbbr", "BuilderId", "MarketId", "MarketName", 
                "CommunityId", "CommunityName", "Latitude", "Longitude", 
                "PrLo", "PrHi", "SftLo", "SftHi", "Type", "ProjectType", 
                "CommunityType", "HomeCount", "QmInCount", "Phone", 
                "IsTrackingNumber", "Addr", "City", "Zip", "SpecId", 
                "Price", "Sft", "Br", "Ba", "Gr"
            ]
            
            for field in fields_to_extract:
                if field in image_data:
                    extracted_data[field] = image_data[field]
            
            # Add new key mappings
            field_mappings = {
                "real_estate_property_price_short": "Price",
                "real_estate_property_price": "Price",
                "real_estate_property_size": "Sft",
                "real_estate_property_bedrooms": "Br",
                "real_estate_property_bathrooms": "Ba",
                "real_estate_property_garage": "Gr"
            }
            
            for new_key, old_key in field_mappings.items():
                if old_key in extracted_data:
                    extracted_data[new_key] = extracted_data[old_key]
                    
            # 添加固定值字段
            extracted_data["real_estate_property_virtual_tour_type"] = "0"
            extracted_data["real_estate_property_price_unit"] = "1"
            extracted_data["real_estate_property_price_prefix"] = "From"
            extracted_data["real_estate_property_price_on_call"] = "0"
            extracted_data["real_estate_additional_features"] = "1"
            extracted_data["real_estate_property_featured"] = "0"
            extracted_data["real_estate_property_country"] = "US"
            # Extract image URLs
            image_urls = set()  # Using set to avoid duplicates
            
            # Process Collections
            if 'Collections' in image_data:
                for collection in image_data['Collections']:
                    # Add URLs from Elements
                    if 'Elements' in collection:
                        for element in collection['Elements']:
                            if 'Url' in element:
                                image_urls.add(element['Url'])
                            # if 'ThumbnailUrl' in element:
                            #     image_urls.add(element['ThumbnailUrl'])
                            
                    # Add URLs from Thumbnails
                    # if 'Thumbnails' in collection:
                    #     for thumbnail in collection['Thumbnails']:
                    #         image_urls.add(thumbnail)
            
            extracted_data["images"] = list(image_urls)
            return extracted_data
            
        except Exception as e:
            print(f"Error extracting image info: {e}")
            return []
    except Exception as e:
        print(f"Error extracting image info: {e}")
        return []

async def extract_structured_data_using_css_extractor():
    print("\n--- Using JsonCssExtractionStrategy for Fast Structured Output ---")

    # 生成带日期的输出文件名
    current_date = datetime.now().strftime("%Y%m%d")
    # output_filename = f"getHotDealProperties_output_{current_date}.json"
    
    # output_filename = f"getHotDealProperties_output_Cary.json"
    # output_filename = f"getHotDealProperties_output_Durham.json"
    output_filename = f"getHotDealProperties_output_Clayton.json"
    
    temp_filename = f"getHotDealProperties_basic_{current_date}.json"
    
    # 初始化房源集合，使用字典以便通过link快速查找
    all_communities_dict = {}
    
    # 如果输出文件存在，读取已有数据
    if os.path.exists(output_filename):
        print(f"\nLoading existing data from {output_filename}...")
        try:
            with open(output_filename, "r", encoding="utf-8") as f:
                existing_communities = json.load(f)
                for community in existing_communities:
                    if "link" in community and community["link"]:
                        all_communities_dict[community["link"]] = community
                print(f"Loaded {len(all_communities_dict)} existing communities")
        except Exception as e:
            print(f"Error loading existing data: {e}")
            all_communities_dict = {}
    
    # Define the extraction schema
    schema = {
        "name": "Community Listings",
        "baseSelector": ".nhs-c-card--housing",  # Base container for each community
        "fields": [
            {"name": "title", "selector": ".nhs-c-card__body h3.nhs-c-card__facts a", "type": "text"},
            {"name": "price", "selector": ".nhs-c-card__body p.nhs-c-card__price span[data-qa='price_label']", "type": "text"},
            {"name": "address", "selector": ".nhs-c-card__body h3.nhs-c-card__facts a", "type": "text"},
            {"name": "address2", "selector": ".nhs-c-card__body h3.nhs-c-card__facts span[data-qa='plan-card-address']", "type": "text"},
            {"name": "details", "selector": ".nhs-c-card__body p.nhs-c-card__facts[data-qa='card_specs']", "type": "text"},
            {"name": "builder", "selector": ".nhs-c-card__body p.nhs-c-card__facts[data-qa='listing_brand']", "type": "text"},
            {"name": "link", "selector": ".nhs-c-card__body h3.nhs-c-card__facts a", "type": "attribute", "attribute": "href"}
        ]
    }
    
    # Create the extraction strategy
    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)

    # 第一阶段：获取所有房源的基本信息
    print("\n=== Phase 1: Collecting Basic Information ===")
    new_communities_count = 0
    updated_communities_count = 0

    # Use the AsyncWebCrawler with the extraction strategy
    async with AsyncWebCrawler(verbose=True, browser_type="chromium", headless=True) as crawler:
        # 遍历前三个页面
        for page_num in range(1, 2):
            # 构建页面URL
            if page_num == 1:
                # url = "https://www.newhomesource.com/homes/ga/atlanta-area?hotdeals=true"
                #夏洛特 (Charlotte) - 该州最大的城市，是重要的金融和商业中心，也是美国第二大银行业中心。
                # url = "https://www.newhomesource.com/homes/nc/charlotte-area/charlotte?hotdeals=true"
                # 格林斯伯勒 (Greensboro) - 该州第三大城市，是重要的教育和工业中心。
                # url = "https://www.newhomesource.com/homes/nc/greensboro-winston-salem-high-point-area?hotdeals=true"
                # 加州的首府是萨克拉门托 (Sacramento)。这座城市位于加州北部，虽然不如洛杉矶或旧金山那么出名，但作为州府，它是加州政治和行政的中心。
                # url = "https://www.newhomesource.com/homes/ca/sacramento-area?hotdeals=true"
                
                
                # url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/cary?hotdeals=true"
                # url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/durham?hotdeals=true"
                # 罗利 (Raleigh) - 州府所在地，与教堂山(Chapel Hill)和达勒姆(Durham)一起构成"研究三角园区"。这里有许多著名大学和研究机构。
                # url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area?hotdeals=true"
                # url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/apex?hotdeals=true"
                # url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/holly-springs?hotdeals=true"
                # url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/fuquay-varina?hotdeals=true"
                # url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/garner?hotdeals=true"
                url = "https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/clayton?hotdeals=true"
            else:
                # url = f"https://www.newhomesource.com/homes/ga/atlanta-area/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/charlotte-area/charlotte/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/greensboro-winston-salem-high-point-area/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/ca/sacramento-area/page-{page_num}?hotdeals=true"
                
                # url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/cary/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/durham/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/apex/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/holly-springs/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/fuquay-varina/page-{page_num}?hotdeals=true"
                # url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/garner/page-{page_num}?hotdeals=true"
                url = f"https://www.newhomesource.com/homes/nc/raleigh-durham-chapel-hill-area/clayton/page-{page_num}?hotdeals=true"
            
            print(f"\nProcessing page {page_num}...")
            print(f"URL: {url}")
            
            result = await crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy,
                cache_mode=False,
                simulate_user=True,
                override_navigator=True
            )

            assert result.success, f"Failed to crawl page {page_num}"

            # Parse the extracted content
            communities = json.loads(result.extracted_content)
            print(f"Found {len(communities)} homes on page {page_num}")
            
            # 添加新的房源，跳过已存在的
            for community in communities:
                if "link" in community and community["link"]:
                    community["page_number"] = page_num
                    if "address2" in community and community["address2"]:
                        community["address"] = community["address"] + " " + community["address2"]
                    if community["link"] not in all_communities_dict:
                        all_communities_dict[community["link"]] = community
                        new_communities_count += 1
                        print(f"New community found: {community['link']}")
                    else:
                        print(f"Community already exists: {community['link']}")
                        updated_communities_count += 1
            
            # 每次处理完一页就保存一次数据
            print(f"\nSaving data after page {page_num} to {output_filename}...")
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(list(all_communities_dict.values()), f, ensure_ascii=False, indent=2)
            
            # 每个页面之间添加延时，避免请求过于频繁
            if page_num < 3:
                delay = random.uniform(10.0, 15.0)
                print(f"\nWaiting {delay:.2f} seconds before processing next page...")
                time.sleep(delay)
        
        # 第二阶段：获取详细信息
        print("\n=== Phase 2: Collecting Detailed Information ===")
        
        # 处理每个房源的详细信息
        scounter = 0
        for index, community in enumerate(all_communities_dict.values()):
            if 42 == scounter:
                break
            scounter += 1
            if "link" in community and community["link"]:
                # 检查是否需要更新详细信息
                needs_update = (
                    "images" not in community or 
                    not community["images"] or len(community["images"]) < 1 or
                    "promotions" not in community or 
                    not community["promotions"] or len(community["promotions"]) < 1
                )
                
                if not needs_update:
                    print(f"\nSkipping community {index + 1} (already has details): {community.get('link', 'N/A')}")
                    continue
                
                print(f"\nProcessing community {index + 1} of {len(all_communities_dict)}")
                print(f"Title: {community.get('address', 'N/A') + '  ' + community.get('address2', 'N/A')}")
                print(f"Link: {community['link']}")
                
                time.sleep(random.uniform(50.0, 80.0))
                full_url = community["link"]
                
                try:
                    print(f"Fetching promos from: {full_url}")
                    promos = await extract_promo_info(full_url, crawler)
                    print(f"Fetching images and details from: {full_url}")
                    images = await extract_image_info(full_url, crawler)
                except Exception as e:
                    print(f"Error fetching details from {full_url}: {e}")
                    continue

                community["promotions"] = promos
                if isinstance(images, dict):
                    community["images"] = images.get("images", [])
                    community.update({k: v for k, v in images.items() if k != "images"})
                else:
                    community["images"] = []
                
                # Add new key-value mappings
                community["title"] = community.get("address", "") + ' ' + community.get("address2", "")
                community["real_estate_property_address"] = community.get("address", "") + ' ' + community.get("address2", "")
                community["community_address"] = community.get("Addr", "") + ',' + community.get("City", "") + ' ' + community.get("StateAbbr", "") + ' ' + community.get("Zip", "")
                community["real_estate_property_zip"] = community.get("Zip", "")
                community["real_estate_property_location"] = {
                    "location": community.get("Latitude", "") + ',' + community.get("Longitude", ""),
                    "address": community.get("address", "") + ' ' + community.get("address2", "")
                }
                # Combine promotions and builder information for content
                promo_texts = [p.get("promo_title", "") for p in promos] if promos else []
                builder_text = community.get("builder", "")
                community["content"] = " ".join(filter(None, promo_texts + [builder_text]))
                
                updated_communities_count += 1
                
                # 保存更新后的数据
                print(f"Saving updated data to {output_filename}")
                with open(output_filename, "w", encoding="utf-8") as f:
                    json.dump(list(all_communities_dict.values()), f, ensure_ascii=False, indent=2)

    print(f"\nAll done!")
    print(f"Total communities: {len(all_communities_dict)}")
    print(f"New communities found: {new_communities_count}")
    print(f"Communities updated with details: {updated_communities_count}")
    print(f"Results saved to: {output_filename}")

# Run the async function
asyncio.run(extract_structured_data_using_css_extractor())