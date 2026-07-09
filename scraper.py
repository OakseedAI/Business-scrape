import re
import urllib.parse
import pandas as pd
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import time

# List of domains that are directories, social media, or irrelevant to small business websites
EXCLUDED_DOMAINS = [
    'yelp.com', 'yellowpages.com', 'superpages.com', 'angie.com', 'angislist.com', 
    'houzz.com', 'facebook.com', 'instagram.com', 'linkedin.com', 'youtube.com', 
    'twitter.com', 'mapquest.com', 'tripadvisor.com', 'groupon.com', 'indeed.com', 
    'bbb.org', 'foursquare.com', 'nextdoor.com', 'patch.com', 'local.yahoo.com', 
    'nytimes.com', 'wikipedia.org', 'pinterest.com', 'reddit.com', 'dx.doi.org', 
    'homedepot.com', 'lowes.com', 'amazon.com', 'google.com'
]

# Signature patterns for common workflow and customer automations
AUTOMATION_SIGNATURES = {
    'Scheduling & Booking': [
        r'calendly\.com', r'acuityscheduling\.com', r'bookafy\.com', r'appointlet\.com',
        r'oncehub\.com', r'scheduleonce\.com', r'setmore\.com', r'simplybook\.me',
        r'vagaro\.com', r'mindbodyonline\.com', r'housecallpro\.com', r'jobber\.com',
        r'servicefusion\.com', r'fieldedge\.com', r'square\.site/appointments',
        r'bookingbug\.com', r'apppointy\.com', r'schedulicity\.com'
    ],
    'Chatbots & Live Chat': [
        r'intercom\.io', r'drift\.com', r'tawk\.to', r'crisp\.chat', r'zendesk\.com',
        r'livechatinc\.com', r'tidio\.co', r'chatport\.com', r'manychat\.com',
        r'chatwidget', r'chatbot', r'activecampaign.*chat', r'hubspot.*chat'
    ],
    'CRM & Marketing Automation': [
        r'hubspot\.com', r'salesforce\.com', r'marketo\.com', r'activecampaign\.com',
        r'infusionsoft\.com', r'keap\.com', r'klaviyo\.com', r'zapier\.com', r'make\.com',
        r'gohighlevel\.com', r'leadpages\.com', r'clickfunnels\.com'
    ],
    'Advanced Web Forms': [
        r'typeform\.com', r'jotform\.com', r'wufoo\.com', r'cognitoforms\.com',
        r'formstack\.com', r'paperform\.co'
    ]
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def clean_company_name(title):
    """Clean search result title to extract a plausible company name."""
    if not title:
        return "Unknown Company"
    # Remove directory suffix patterns
    title = re.sub(r'\b(Yelp|Yellow\s*Pages|Facebook|LinkedIn|TripAdvisor)\b.*$', '', title, flags=re.IGNORECASE)
    # Remove city/state patterns commonly appended in search results (e.g., " - Raleigh, NC")
    title = re.sub(r'[-\s|]+(Raleigh|Durham|Cary|Charlotte|Greensboro|Winston-Salem|Fayetteville|Wilmington|Apex|Wake\s*Forest|NC|North\s*Carolina)\b.*$', '', title, flags=re.IGNORECASE)
    # Clean up standard characters
    title = title.strip(' -|*')
    return title if title else "Unknown Company"

def get_domain(url):
    """Extract root domain from a URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""

def is_valid_business_url(url):
    """Check if the URL belongs to an actual business website rather than a directory."""
    domain = get_domain(url)
    if not domain:
        return False
    
    # Check if domain or parts of domain match excluded domains
    for d in EXCLUDED_DOMAINS:
        if d in domain:
            return False
            
    # Avoid files, images, etc.
    if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.zip']):
        return False
        
    return True

def fetch_html(url, timeout=10):
    """Fetch HTML content with standard browser headers."""
    try:
        # Standardize URL
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def extract_contact_info(soup, html_content, base_url):
    """Extract emails and phone numbers from the parsed HTML content."""
    emails = set()
    phones = set()
    
    # 1. Search hrefs for mailto and tel links (most reliable)
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        if href.startswith('mailto:'):
            email = href.replace('mailto:', '').split('?')[0].strip()
            if email:
                emails.add(email)
        elif href.startswith('tel:'):
            phone = href.replace('tel:', '').strip()
            # Clean non-digits except +
            phone = re.sub(r'[^\d+]', '', phone)
            if phone:
                phones.add(phone)
                
    # 2. General Regex Search for Emails in text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found_emails = re.findall(email_pattern, html_content)
    for email in found_emails:
        # Exclude common image extensions or fake emails
        if not any(email.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', 'w3.org']):
            emails.add(email.lower())
            
    # 3. General Regex Search for Phone Numbers in text
    # Matches formats: (123) 456-7890, 123-456-7890, 123 456 7890
    phone_pattern = r'(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})'
    found_phones = re.findall(phone_pattern, html_content)
    for phone in found_phones:
        formatted = f"({phone[0]}) {phone[1]}-{phone[2]}"
        phones.add(formatted)
        
    return list(emails), list(phones)

def detect_automations(html_content):
    """Scan HTML for signs of known workflow automation scripts and widgets."""
    detected = []
    
    if not html_content:
        return detected
        
    for category, regex_list in AUTOMATION_SIGNATURES.items():
        category_matched = False
        for regex in regex_list:
            if re.search(regex, html_content, re.IGNORECASE):
                detected.append(category)
                category_matched = True
                break
                
    return list(set(detected))

def find_sub_pages(soup, base_url):
    """Find links to Contact, About, and Team pages to search for email/phone."""
    sub_pages = []
    domain = get_domain(base_url)
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.text.lower().strip()
        
        # Look for contact/about/team links
        is_target = any(keyword in text for keyword in ['contact', 'about', 'team', 'staff', 'reach', 'info', 'book'])
        
        if is_target:
            # Resolve relative URLs
            full_url = urllib.parse.urljoin(base_url, href)
            # Make sure it's on the same domain
            if get_domain(full_url) == domain and full_url != base_url:
                sub_pages.append(full_url)
                
    return list(set(sub_pages))[:3] # Limit to top 3 sub-pages to keep it fast

def crawl_business_site(url):
    """Fully crawl a business site's homepage and contacts to gather data."""
    result = {
        'emails': [],
        'phones': [],
        'automations': [],
        'automation_status': 'Likely None (No code signatures found)'
    }
    
    html = fetch_html(url)
    if not html:
        return result
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract contacts and check automations on Homepage
    emails, phones = extract_contact_info(soup, html, url)
    automations = detect_automations(html)
    
    result['emails'].extend(emails)
    result['phones'].extend(phones)
    result['automations'].extend(automations)
    
    # Try sub-pages for contact info if homepage didn't yield emails
    if not result['emails']:
        sub_pages = find_sub_pages(soup, url)
        for page in sub_pages:
            sub_html = fetch_html(page)
            if sub_html:
                sub_soup = BeautifulSoup(sub_html, 'html.parser')
                sub_emails, sub_phones = extract_contact_info(sub_soup, sub_html, page)
                sub_autos = detect_automations(sub_html)
                
                result['emails'].extend(sub_emails)
                result['phones'].extend(sub_phones)
                result['automations'].extend(sub_autos)
                
    # Clean duplicates
    result['emails'] = list(set(result['emails']))
    result['phones'] = list(set(result['phones']))
    result['automations'] = list(set(result['automations']))
    
    if result['automations']:
        result['automation_status'] = f"Uses: {', '.join(result['automations'])}"
    else:
        result['automation_status'] = "Likely None (No code signatures found)"
        
    return result

def run_lead_search(city, business_type, max_results=15):
    """Query Mojeek (primary) and DuckDuckGo (fallback) for local businesses, crawl sites, and compile results."""
    # Build query
    search_query = f"{business_type} {city} NC"
    print(f"Running search for query: {search_query}")
    
    leads = []
    scraped_count = 0
    search_results = []
    
    # 1. Try Mojeek Search (very script-friendly)
    try:
        url = f"https://www.mojeek.com/search?q={urllib.parse.quote(search_query)}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Extract links from Mojeek headings
            for h2 in soup.find_all(['h2', 'h3']):
                a = h2.find('a', href=True)
                if a:
                    href = a['href']
                    if href.startswith('http') and is_valid_business_url(href):
                        title = a.text.strip()
                        company_name = clean_company_name(title)
                        search_results.append({
                            'url': href,
                            'title': company_name,
                            'snippet': ''
                        })
            print(f"Mojeek returned {len(search_results)} candidates.")
    except Exception as e:
        print(f"Error querying Mojeek: {e}")
        
    # 2. Fallback to DuckDuckGo search if Mojeek failed
    if not search_results:
        print("Mojeek returned no candidates, trying DuckDuckGo fallback...")
        try:
            with DDGS() as ddgs:
                ddg_results = ddgs.text(f"{search_query} website", max_results=max_results * 2)
                for r in ddg_results:
                    url = r.get('href')
                    if url and is_valid_business_url(url):
                        title = clean_company_name(r.get('title'))
                        search_results.append({
                            'url': url,
                            'title': title,
                            'snippet': r.get('body', '')
                        })
                print(f"DuckDuckGo fallback returned {len(search_results)} candidates.")
        except Exception as e:
            print(f"Error querying DuckDuckGo: {e}")
            
    # Deduplicate candidate websites by domain
    unique_candidates = []
    seen_domains = set()
    for res in search_results:
        dom = get_domain(res['url'])
        if dom and dom not in seen_domains:
            seen_domains.add(dom)
            unique_candidates.append(res)
            
    # Process/Crawl each candidate website
    for res in unique_candidates:
        if scraped_count >= max_results:
            break
            
        url = res['url']
        company_name = res['title']
        snippet = res['snippet']
        
        print(f"Processing ({scraped_count+1}/{max_results}): {company_name} ({url})")
        
        # Crawl the business site
        crawl_data = crawl_business_site(url)
        
        # Formulate the email address (prefer crawling, fallback to searching snippets)
        email = crawl_data['emails'][0] if crawl_data['emails'] else ""
        if not email and snippet:
            # Fallback email extraction from snippet
            snippet_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
            if snippet_emails:
                email = snippet_emails[0]
                
        # Formulate phone (prefer crawling, fallback to snippet or blank)
        phone = crawl_data['phones'][0] if crawl_data['phones'] else ""
        if not phone and snippet:
            # Fallback phone from snippet
            snippet_phones = re.findall(r'(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})', snippet)
            if snippet_phones:
                phone = f"({snippet_phones[0][0]}) {snippet_phones[0][1]}-{snippet_phones[0][2]}"
                
        leads.append({
            'Company Name': company_name,
            'City': city,
            'Business Type': business_type,
            'Phone': phone,
            'Email': email,
            'Website': url,
            'Automation Status': crawl_data['automation_status'],
            'Likely Lacks Automation': 'Yes' if not crawl_data['automations'] else 'No',
            'Status': 'New Lead'
        })
        scraped_count += 1
        time.sleep(1) # Polite crawling delay
        
    return leads

def save_leads_to_excel(new_leads, filepath='leads.xlsx'):
    """Append new leads to Excel file, avoiding duplicate domains."""
    try:
        try:
            existing_df = pd.read_excel(filepath)
        except FileNotFoundError:
            existing_df = pd.DataFrame(columns=[
                'Company Name', 'City', 'Business Type', 'Phone', 'Email', 
                'Website', 'Automation Status', 'Likely Lacks Automation', 'Status'
            ])
            
        new_df = pd.DataFrame(new_leads)
        
        if existing_df.empty:
            final_df = new_df
        else:
            # Avoid writing duplicates by matching websites/domains
            existing_df['Domain'] = existing_df['Website'].apply(get_domain)
            new_df['Domain'] = new_df['Website'].apply(get_domain)
            
            # Keep rows from new_df that are not already present in existing_df
            new_df_filtered = new_df[~new_df['Domain'].isin(existing_df['Domain'])]
            new_df_filtered = new_df_filtered.drop(columns=['Domain'])
            existing_df = existing_df.drop(columns=['Domain'])
            
            final_df = pd.concat([existing_df, new_df_filtered], ignore_index=True)
            
        final_df.to_excel(filepath, index=False)
        return len(final_df) - len(existing_df) # Return count of newly added rows
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        return 0
