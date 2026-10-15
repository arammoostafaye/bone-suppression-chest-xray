"""
Medal PACS Automated Downloader & Cache Manager
Boali Hospital Marivan (بیمارستان بوعلی مریوان)

Supports:
1. SMS links: https://marivan-pacs-boali.muk.ac.ir/?query=...
2. Direct SeriesList links: https://marivan-pacs-boali.muk.ac.ir/MedalWeb/serieslist.aspx?SK=...
3. Direct Viewer links: https://marivan-pacs-boali.muk.ac.ir/MedalWeb/viewer.aspx?SK=...
4. Raw SMS text (auto regex extraction)
5. Temp Cache cleanup & size monitoring
"""

import os
import re
import sys
import shutil
import zipfile
import urllib.request
import urllib.parse
import http.cookiejar
import ssl

DEFAULT_BASE_URL = "https://marivan-pacs-boali.muk.ac.ir"
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class PacsCacheManager:
    """Manages temporary downloads to prevent disk bloating on C:\\."""
    def __init__(self, cache_dir="pacs_temp_cache"):
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_size_bytes(self):
        total_size = 0
        if not os.path.exists(self.cache_dir):
            return 0
        for dirpath, dirnames, filenames in os.walk(self.cache_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def get_cache_size_formatted(self):
        bytes_val = self.get_cache_size_bytes()
        if bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

    def clear_cache(self):
        """Safely removes all temporary downloaded and unzipped PACS files."""
        deleted_count = 0
        freed_bytes = self.get_cache_size_bytes()
        if os.path.exists(self.cache_dir):
            for item in os.listdir(self.cache_dir):
                item_path = os.path.join(self.cache_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Warning: Could not remove {item_path}: {e}")
        os.makedirs(self.cache_dir, exist_ok=True)
        return freed_bytes, deleted_count


class MedalPacsClient:
    """Automates image acquisition from Boali Hospital Medal PACS."""
    def __init__(self, cache_manager=None, base_url=DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.cache_mgr = cache_manager or PacsCacheManager()
        self.cookie_jar = http.cookiejar.CookieJar()
        
        # Configure SSL context (ignoring self-signed certs)
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

        # Setup opener with cookies
        cookie_handler = urllib.request.HTTPCookieProcessor(self.cookie_jar)
        https_handler = urllib.request.HTTPSHandler(context=self.ssl_ctx)
        self.opener = urllib.request.build_opener(cookie_handler, https_handler)

    def extract_link(self, raw_input):
        """Extracts URL from arbitrary text (like a full Persian SMS)."""
        text = raw_input.strip()
        url_match = re.search(r"https?://[^\s<>\"']+", text)
        if url_match:
            return url_match.group(0)
        return text

    def parse_input(self, raw_input):
        """
        Determines the type of link:
        - SMS link with ?query=
        - Direct serieslist.aspx?SK=
        - Direct viewer.aspx?SK=
        - Pure token
        """
        link = self.extract_link(raw_input)

        if "query=" in link:
            # Format: https://.../?query=TOKEN=N/A or ./guest.aspx?query=...
            token_match = re.search(r"query=([^&\s]+)", link)
            token = token_match.group(1) if token_match else ""
            return {"type": "sms", "url": link, "token": token}
        
        if "SK=" in link:
            # Direct MedalWeb link
            sk_match = re.search(r"SK=([^&\s]+)", link)
            sk = sk_match.group(1) if sk_match else ""
            return {"type": "direct_sk", "url": link, "sk": sk}

        # Raw token
        return {"type": "raw_token", "url": None, "sk": link}

    def fetch_url(self, url, headers=None, data=None):
        req_headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fa,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=req_headers)
        with self.opener.open(req, timeout=30) as resp:
            content = resp.read()
            return resp.geturl(), content

    def download_study(self, user_input, mode=0, progress_callback=None):
        """
        Full automated pipeline:
        1. Authenticate (via SMS query or direct SK)
        2. Extract PID, PName, and series info
        3. Request zip archive from Download.aspx
        4. Stream-download zip file to cache
        5. Extract files and catalog DICOM series
        """
        parsed = self.parse_input(user_input)
        if progress_callback: progress_callback(10, "شناسایی لینک و آغاز ارتباط با پکس...")

        # Step 1: Establish Session
        if parsed["type"] == "sms":
            sms_url = parsed["url"]
            if not sms_url.startswith("http"):
                sms_url = f"{self.base_url}/?query={sms_url}"
            final_url, html_bytes = self.fetch_url(sms_url)
            html = html_bytes.decode("utf-8", errors="replace")
            
            # Extract SK from redirect or serieslist
            sk_match = re.search(r"SK=([^&\"'\s]+)", final_url) or re.search(r"SK=([^&\"'\s]+)", html)
            sk = sk_match.group(1) if sk_match else parsed["token"].replace("=N/A", "")
        else:
            sk = parsed["sk"]
            # Visit serieslist directly to establish session
            series_url = f"{self.base_url}/MedalWeb/serieslist.aspx?SK={sk}"
            final_url, html_bytes = self.fetch_url(series_url)
            html = html_bytes.decode("utf-8", errors="replace")

        if progress_callback: progress_callback(30, "استخراج مشخصات بیمار و سری‌ها...")

        # Step 2: Extract Patient Metadata
        pid_match = re.search(r'id=["\']?PIDTitle["\']?[^>]*>([^<]+)<', html) or re.search(r"PID:\s*([0-9A-Za-z\-_]+)", html)
        pname_match = re.search(r'id=["\']?PNameTitle["\']?[^>]*>([^<]+)<', html) or re.search(r"PName:\s*([^<\r\n\t]+)", html)
        
        pid = pid_match.group(1).strip() if pid_match else "UNKNOWN_PID"
        pname = pname_match.group(1).strip() if pname_match else "UNKNOWN_PNAME"

        # Step 3: Trigger Viewer.aspx to ensure session readiness
        viewer_url = f"{self.base_url}/MedalWeb/viewer.aspx?SK={sk}&Ser=1"
        try:
            self.fetch_url(viewer_url, headers={"Referer": f"{self.base_url}/MedalWeb/serieslist.aspx?SK={sk}"})
        except Exception:
            pass

        if progress_callback: progress_callback(50, f"درخواست ساخت پکیج دایکام برای {pname}...")

        # Step 4: Request Zip build via POST to Download.aspx
        download_api = f"{self.base_url}/MedalWeb/Download.aspx?SK={sk}&PID={pid}&mode={mode}"
        post_headers = {
            "Referer": viewer_url,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Length": "0"
        }
        _, resp_bytes = self.fetch_url(download_api, headers=post_headers, data=b"")
        zip_filename = resp_bytes.decode("utf-8", errors="replace").strip()
        
        if not zip_filename.endswith(".zip"):
            # Try to match zip name from output
            zm = re.search(r"([0-9A-Za-z\-_]+\.zip)", zip_filename)
            if zm:
                zip_filename = zm.group(1)
            else:
                raise RuntimeError(f"خطا در ساخت فایل توسط سرور پکس: {zip_filename}")

        if progress_callback: progress_callback(70, f"در حال دانلود فایل {zip_filename} از سرور...")

        # Step 5: Download the generated zip file
        zip_url = f"{self.base_url}/MedalWeb/temp/{zip_filename}"
        zip_save_path = os.path.join(self.cache_mgr.cache_dir, zip_filename)

        req = urllib.request.Request(zip_url, headers={"User-Agent": DEFAULT_UA, "Referer": viewer_url})
        with self.opener.open(req, timeout=120) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024
            with open(zip_save_path, "wb") as out_f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and progress_callback:
                        pct = int(70 + (downloaded / total_size) * 20)
                        progress_callback(pct, f"دانلود فایل دایکام: {downloaded // (1024*1024)}/{total_size // (1024*1024)} MB")

        if progress_callback: progress_callback(92, "استخراج فایل‌های دایکام و چینش نماها...")

        # Step 6: Extract the zip file
        extract_folder = os.path.join(self.cache_mgr.cache_dir, f"study_{pid}")
        os.makedirs(extract_folder, exist_ok=True)
        with zipfile.ZipFile(zip_save_path, 'r') as zf:
            zf.extractall(extract_folder)

        # Step 7: Catalog DICOM files
        dicom_files = []
        for root, _, files in os.walk(extract_folder):
            for file in sorted(files):
                if file.lower().endswith(('.dcm', '.dicom', '.ima')) or (len(file) <= 8 and not '.' in file):
                    dicom_files.append(os.path.join(root, file))

        if progress_callback: progress_callback(100, "اتمام موفقیت‌آمیز دریافت از پکس.")

        return {
            "pid": pid,
            "pname": pname,
            "zip_path": zip_save_path,
            "extract_folder": extract_folder,
            "dicom_files": dicom_files,
            "count": len(dicom_files)
        }
