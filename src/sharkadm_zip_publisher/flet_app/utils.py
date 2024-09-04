def fix_url_str(url: str) -> str:
    prefix = 'https://'
    url = url.strip().replace('\\', '/').strip('/')
    if not url:
        return ''
    if not url.startswith(prefix):
        url = prefix + url
    return url